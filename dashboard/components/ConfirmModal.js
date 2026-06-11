import React from 'react';

export default function ConfirmModal({ isOpen, title, message, onConfirm, onCancel, confirmColor }) {
  if (!isOpen) return null;

  const confirmBtnClass = confirmColor === 'red'
    ? 'bg-[#f85149] hover:bg-[#f85149]/80 text-[#e6edf3] border-[#f85149]'
    : 'bg-[#58a6ff] hover:bg-[#58a6ff]/80 text-[#0d1117] border-[#58a6ff]';

  return (
    <div 
      className="absolute top-0 left-0 w-full min-h-screen bg-black/60 flex items-center justify-center p-4 z-50"
      style={{ backdropFilter: 'blur(4px)' }}
    >
      <div className="bg-[#1c2128] border border-[#30363d] rounded-lg max-w-md w-full p-6 shadow-2xl animate-pulse-slow">
        <h3 className="text-lg font-semibold text-[#e6edf3] mb-2">{title}</h3>
        <p className="text-sm text-[#7d8590] mb-6 leading-relaxed">{message}</p>
        <div className="flex justify-end space-x-3">
          <button
            onClick={onCancel}
            type="button"
            className="px-4 py-2 text-sm font-semibold rounded-lg bg-[#21262d] border border-[#30363d] hover:bg-[#30363d] text-[#e6edf3] transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            type="button"
            className={`px-4 py-2 text-sm font-semibold rounded-lg border transition-colors ${confirmBtnClass}`}
          >
            Confirm
          </button>
        </div>
      </div>
    </div>
  );
}
