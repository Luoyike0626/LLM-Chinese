# LLM Council — 大模型议会（中文版）

![llmcouncil](header.jpg)

> 本项目 fork 自 [karpathy/llm-council](https://github.com/karpathy/llm-council)，进行了全面的中文本地化改造。

## 项目简介

与其只问一个你最喜欢的 LLM（如 GPT、Gemini、Claude），不如组建一个「大模型议会」来共同审议你的问题。

这是一个本地运行的 Web 应用，界面类似 ChatGPT，但背后是**三阶段审议流程**：

1. **第一阶段：独立回答** — 用户问题同时发送给多个大模型，收集各自的回答。所有回答以标签页展示，可逐一查看。
2. **第二阶段：同行评审** — 各模型对匿名化后的回答进行评审和排名。关键设计：模型看到的是「回答A、回答B、回答C」，不知道哪个回答是哪个模型写的，从而避免偏袒自己。
3. **第三阶段：最终答案** — 议会主席综合所有回答和评审意见，生成最终答案。

## 本分支改动

相比原版 [karpathy/llm-council](https://github.com/karpathy/llm-council)，本仓库做了以下改动：

### 🀄 全面中文化
- **前端界面**：所有 UI 文字（标题、按钮、提示、加载状态等）全部翻译为中文
- **后端提示词**：三个阶段 + 标题生成的提示词全部改为中文，模型输出也会是中文
- 议会名称改为「大模型议会」

### 🔧 API 后端切换
- 从 **OpenRouter** 切换为 **SiliconFlow（硅基流动）**，使用国产模型
- API 端点：`https://api.siliconflow.cn/v1/chat/completions`
- 环境变量改为 `SILICONFLOW_API_KEY`

### 🐛 Bug 修复
- **CORS 400 错误**：`allow_origins` 改为 `["*"]`，解决浏览器 OPTIONS 预检请求被拒的问题
- **输入框消失**：修复回答结束后输入框不显示的问题，现在支持连续多轮对话
- **模型失效**：原配置中的 `Qwen/Qwen3-235B-A22B` 和 `Pro/zai-org/GLM-4.5` 已在 SiliconFlow 下架，替换为当前可用的最新模型

### 📦 当前议会成员

| 角色 | 模型 |
|---|---|
| 议员 | `deepseek-ai/DeepSeek-V3` |
| 议员 | `deepseek-ai/DeepSeek-R1`（推理特化） |
| 议员 | `Qwen/Qwen3.5-397B-A17B`（通义千问3.5 超大规模 MoE） |
| 议员 | `Pro/zai-org/GLM-5.1`（智谱 GLM 最新旗舰） |
| 主席 | `deepseek-ai/DeepSeek-R1` |

模型配置在 `backend/config.py` 中，可按需修改。

## 使用方法

### 1. 安装依赖

**后端（Python）：**
```bash
pip install fastapi uvicorn httpx python-dotenv pydantic
```

**前端（Node.js）：**
```bash
cd frontend
npm install
cd ..
```

### 2. 配置 API Key

在项目根目录创建 `.env` 文件：

```bash
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

> 在 [siliconflow.cn](https://siliconflow.cn) 注册即可获取 API Key。注意：部分模型（如 `Pro/` 前缀的）需要充值才能使用。

### 3. 自定义模型（可选）

编辑 `backend/config.py`：

```python
COUNCIL_MODELS = [
    "deepseek-ai/DeepSeek-V3",
    "deepseek-ai/DeepSeek-R1",
    "Qwen/Qwen3.5-397B-A17B",
    "Pro/zai-org/GLM-5.1",
]

CHAIRMAN_MODEL = "deepseek-ai/DeepSeek-R1"
```

> 可在 [SiliconFlow 模型广场](https://cloud.siliconflow.cn/models) 浏览所有可用模型。

### 4. 启动应用

**终端 1 — 启动后端（端口 8001）：**
```bash
python -m backend.main
```

**终端 2 — 启动前端（端口 5173）：**
```bash
cd frontend
npm run dev
```

然后浏览器打开 `http://localhost:5173` 即可使用。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI (Python)、httpx 异步请求、SiliconFlow API |
| 前端 | React + Vite、react-markdown 渲染 |
| 存储 | JSON 文件（`data/conversations/`） |

## 原版说明

> 本项目 99% 是 vibe code 产物，是 [Andrej Karpathy](https://github.com/karpathy) 在某个周六为了「和 LLM 一起读书」而做的 side project。不会持续维护，仅供参考和启发。[原版 README](https://github.com/karpathy/llm-council)
