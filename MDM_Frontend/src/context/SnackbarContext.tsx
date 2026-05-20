/**
 * src/context/SnackbarContext.tsx
 * ---------------------------------
 * Global notification service that renders stackable toast messages
 * with rich design styles and interactive pause-on-hover logic.
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';
import '../components/SnackbarContainer.css';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

interface SnackbarContextValue {
  showSuccess: (message: string, duration?: number) => void;
  showError: (message: string, duration?: number) => void;
  showWarning: (message: string, duration?: number) => void;
  showInfo: (message: string, duration?: number) => void;
  removeToast: (id: string) => void;
}

const SnackbarContext = createContext<SnackbarContextValue | null>(null);

const TOAST_ICONS: Record<ToastType, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
};

export function SnackbarProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const addToast = useCallback((message: string, type: ToastType, duration = 4000) => {
    const id = crypto.randomUUID();
    setToasts(prev => [...prev, { id, message, type, duration }]);

    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }
  }, [removeToast]);

  const showSuccess = useCallback((msg: string, dur?: number) => addToast(msg, 'success', dur), [addToast]);
  const showError = useCallback((msg: string, dur?: number) => addToast(msg, 'error', dur), [addToast]);
  const showWarning = useCallback((msg: string, dur?: number) => addToast(msg, 'warning', dur), [addToast]);
  const showInfo = useCallback((msg: string, dur?: number) => addToast(msg, 'info', dur), [addToast]);

  return (
    <SnackbarContext.Provider value={{ showSuccess, showError, showWarning, showInfo, removeToast }}>
      {children}
      <div className="sb-container">
        {toasts.map(t => (
          <div
            key={t.id}
            className={`sb-toast sb-toast--${t.type}`}
            role="alert"
          >
            <span className="sb-toast__icon">{TOAST_ICONS[t.type]}</span>
            <span className="sb-toast__message">{t.message}</span>
            <button
              className="sb-toast__close"
              onClick={() => removeToast(t.id)}
              aria-label="Close notification"
            >
              ✕
            </button>
            {t.duration && t.duration > 0 && (
              <div
                className="sb-toast__progress"
                style={{ animationDuration: `${t.duration}ms` }}
              />
            )}
          </div>
        ))}
      </div>
    </SnackbarContext.Provider>
  );
}

export function useSnackbar(): SnackbarContextValue {
  const ctx = useContext(SnackbarContext);
  if (!ctx) {
    throw new Error('useSnackbar must be used within a SnackbarProvider');
  }
  return ctx;
}
