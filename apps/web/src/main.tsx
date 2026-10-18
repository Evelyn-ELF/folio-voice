import { useState } from 'react';
import { createRoot } from 'react-dom/client';
import type { HealthLive } from '../../../packages/contracts/generated';
import './style.css';

function App() {
  const [status, setStatus] = useState('尚未检查连接');
  const [pending, setPending] = useState(false);
  async function checkConnection() {
    setPending(true);
    setStatus('正在检查连接…');
    try {
      const response = await fetch('/api/v1/health/live', { signal: AbortSignal.timeout(4000) });
      const value: unknown = await response.json();
      if (!response.ok || !value || typeof value !== 'object' || !('status' in value) || value.status !== 'alive') {
        throw new Error('响应不符合存活契约');
      }
      const live: HealthLive = { status: value.status };
      setStatus(live.status === 'alive' ? '已连接应用' : '连接失败');
    } catch {
      setStatus('连接失败，请确认应用已启动后重试');
    } finally {
      setPending(false);
    }
  }
  return <main>
    <p className="brand">Folio Voice</p>
    <h1>让文字成为声音</h1>
    <p>书籍导入、声音管理和制作功能正在开发中。</p>
    <section aria-labelledby="connection">
      <h2 id="connection">应用连接</h2>
      <p role="status">{status}</p>
      <button disabled={pending} onClick={() => void checkConnection()}>检查连接</button>
      <p className="note">连接成功表示应用进程可访问，制作服务尚未就绪。</p>
    </section>
  </main>;
}

const root = document.getElementById('root');
if (!root) throw new Error('页面缺少显示区域');
createRoot(root).render(<App />);
