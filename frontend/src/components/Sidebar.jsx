import { useState, useEffect } from 'react';
import './Sidebar.css';

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
}) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>大模型议会</h1>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + 新建对话
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">暂无对话</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title">
                {conv.title || '新对话'}
              </div>
              <div className="conversation-meta">
                {conv.message_count} 条消息
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
