type WebSocketEventHandler = (data: any) => void;

const AUTH_EXPIRED_CLOSE_CODE = 4401;
const AUTH_EXPIRED_EVENT = 'auth:expired';

function buildWebSocketUrl(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host; // This includes port if present
  const token = localStorage.getItem('auth_token') || '';
  const query = token ? `?token=${encodeURIComponent(token)}` : '';
  return `${protocol}//${host}/ws${query}`;
}

class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectInterval = 3000;
  private listeners: Map<string, WebSocketEventHandler[]> = new Map();
  public isConnected = false;
  private shouldConnect = false;

  constructor() {
    // 延迟连接，等待认证完成
    // 只有在已登录时才尝试连接
    if (localStorage.getItem('auth_logged_in') === 'true') {
      this.connect();
    }
  }

  public start() {
    // 手动启动 WebSocket 连接
    this.shouldConnect = true;
    if (!this.ws || this.ws.readyState === WebSocket.CLOSED) {
      this.connect();
    }
  }

  public stop() {
    // 停止 WebSocket 连接
    this.shouldConnect = false;
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  private connect() {
    const url = buildWebSocketUrl();

    console.log(`Connecting to WebSocket at ${url.replace(/([?&])token=[^&]*/, '$1token=***')}`);
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.isConnected = true;
      this.emit('connected', { isConnected: true });
    };

    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        // Expecting message format: { type: 'event_type', data: ... }
        if (message.type) {
          this.emit(message.type, message.data);
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message', e);
      }
    };

    this.ws.onclose = (event) => {
      // 4401 表示 token 无效或已过期：停止重连并通知登出
      if (event.code === AUTH_EXPIRED_CLOSE_CODE) {
        console.warn('WebSocket 认证失效，停止重连');
        this.shouldConnect = false;
        this.isConnected = false;
        window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
        return;
      }

      if (this.isConnected) {
        console.log('WebSocket disconnected');
        this.isConnected = false;
        this.emit('disconnected', { isConnected: false });
      }
      // 只有在 shouldConnect 为 true 或已登录时才重连
      if (this.shouldConnect || localStorage.getItem('auth_logged_in') === 'true') {
        setTimeout(() => this.connect(), this.reconnectInterval);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      // Close will trigger onclose which handles reconnect
      this.ws?.close();
    };
  }

  public on(event: string, handler: WebSocketEventHandler) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)?.push(handler);
  }

  public off(event: string, handler: WebSocketEventHandler) {
    const handlers = this.listeners.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
    }
  }

  private emit(event: string, data: any) {
    const handlers = this.listeners.get(event);
    if (handlers) {
      handlers.forEach((handler) => handler(data));
    }
  }
}

// Export a singleton instance
export const wsService = new WebSocketService();
