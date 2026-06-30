"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL, TITLE_MODEL


def _build_conversation_context(history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Build message list from conversation history for model context.

    Converts the stored conversation format to a simple list of
    user/assistant messages suitable for LLM API calls.
    """
    context = []
    for msg in history:
        if msg["role"] == "user":
            context.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "assistant" and msg.get("stage3"):
            # Use the final council answer as the assistant's response
            context.append({"role": "assistant", "content": msg["stage3"]["response"]})
    return context


def _build_history_text(history: List[Dict[str, Any]]) -> str:
    """
    Build a text summary of conversation history for inclusion in prompts.
    """
    if not history:
        return "（无历史对话）"

    lines = []
    for i, msg in enumerate(history):
        if msg["role"] == "user":
            lines.append(f"用户（第{i//2 + 1}轮）：{msg['content']}")
        elif msg["role"] == "assistant" and msg.get("stage3"):
            lines.append(f"议会回答（第{i//2 + 1}轮）：{msg['stage3']['response'][:500]}")
    return "\n\n".join(lines)


async def stage1_collect_responses(
    user_query: str,
    conversation_history: List[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        conversation_history: Previous messages in the conversation

    Returns:
        List of dicts with 'model' and 'response' keys
    """
    # Build message list with conversation history for context
    messages = [
        {"role": "system", "content": "你是大模型议会的议员之一，由 DeepSeek-R1 担任主席。请始终使用中文直接回答用户的问题，不要自称主席或扮演主席角色。注意查看对话历史，结合上下文理解用户的追问。"},
    ]
    if conversation_history:
        messages.extend(_build_conversation_context(conversation_history))
    messages.append({"role": "user", "content": user_query})

    # Query all models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage1_results = []
    for model, response in responses.items():
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    conversation_history: List[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        conversation_history: Previous messages in the conversation

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    # Build conversation history text
    history_text = _build_history_text(conversation_history or [])

    ranking_prompt = f"""你正在评估针对以下问题的不同回答，请使用中文进行评价。

对话历史：
{history_text}

当前问题：{user_query}

以下是不同模型对当前问题的回答（已匿名化）：

{responses_text}

你的任务：
1. 首先，逐一评估每个回答。对每个回答，说明它的优点和不足。
2. 然后，在你的回答末尾给出最终排名。

重要：最终排名必须严格按以下格式：
- 以"FINAL RANKING:"（全大写，带冒号）开头
- 然后按从最好到最差的顺序列出编号
- 每行格式：数字、句点、空格，然后仅写回答标签（例如 "1. Response A"）
- 排名部分不要添加任何其他文字或解释

正确的完整回答格式示例：

回答A在X方面提供了很好的细节，但在Y方面有所欠缺...
回答B在准确性上表现不错，但在Z方面深度不够...
回答C提供了最全面的答案...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

现在请提供你的评价和排名："""

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]],
    conversation_history: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        conversation_history: Previous messages in the conversation

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    history_text = _build_history_text(conversation_history or [])

    chairman_prompt = f"""你是大模型议会的主席。多个AI模型已对用户的问题给出了回答，并相互进行了排名评审。

对话历史：
{history_text}

当前问题：{user_query}

第一阶段 - 独立回答：
{stage1_text}

第二阶段 - 同行评审：
{stage2_text}

作为主席，你的任务是将以上所有信息综合成一个全面、准确的答案来回答用户的问题。请考虑：
- 各模型独立回答的内容和洞见
- 同行评审中揭示的回答质量差异
- 一致或分歧的模式

请使用中文，提供一个清晰、有理有据的最终答案，代表议会的集体智慧："""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "错误：无法生成最终综合答案。"
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Supports both English and Chinese formatting:
    - "1. Response A" / "1. 回答A" / "1. 答案A"
    - Fallback to any "Response X" / "回答X" / "答案X" in order

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Determine which label format to look for
    # Check if the model used Chinese labels
    uses_chinese = bool(re.search(r'回答[A-Z]|答案[A-Z]', ranking_text))
    label_pattern = r'回答 ([A-Z])|答案 ([A-Z])' if uses_chinese else r'Response ([A-Z])'

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]

            # Try numbered list: "1. Response A" or "1、回答A"
            numbered_matches = re.findall(
                r'\d+[\.\、\)]\s*(?:Response|回答|答案)\s*([A-Z])',
                ranking_section
            )
            if numbered_matches:
                return [f"Response {m}" for m in numbered_matches]

            # Fallback: extract all labels in order of appearance
            all_matches = re.findall(r'(?:Response|回答|答案)\s*([A-Z])', ranking_section)
            if all_matches:
                return [f"Response {m}" for m in all_matches]

    # Fallback: search entire text for labels in order
    all_matches = re.findall(r'(?:Response|回答|答案)\s*([A-Z])', ranking_text)
    return [f"Response {m}" for m in all_matches]


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        # Use the pre-parsed ranking (same one shown in "Extracted Ranking" on frontend)
        parsed_ranking = ranking.get('parsed_ranking', [])
        if not parsed_ranking:
            # Fallback: re-parse if pre-parsed is empty (shouldn't happen)
            parsed_ranking = parse_ranking_from_text(ranking.get('ranking', ''))

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""请为以下问题生成一个简短的中文标题（最多10个字），简洁且具有描述性。不要使用引号或标点符号。

问题：{user_query}

标题："""

    messages = [{"role": "user", "content": title_prompt}]

    # Use a fast/cheap model for title generation
    response = await query_model(TITLE_MODEL, messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "新对话"

    title = response.get('content', '新对话').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(
    user_query: str,
    conversation_history: List[Dict[str, Any]] = None
) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question
        conversation_history: Previous messages for context

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Stage 1: Collect individual responses (with conversation context)
    stage1_results = await stage1_collect_responses(user_query, conversation_history)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "所有模型均未能响应，请重试。"
        }, {}

    # Stage 2: Collect rankings (with conversation context)
    stage2_results, label_to_model = await stage2_collect_rankings(
        user_query, stage1_results, conversation_history
    )

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer (with conversation context)
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        conversation_history
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings
    }

    return stage1_results, stage2_results, stage3_result, metadata
