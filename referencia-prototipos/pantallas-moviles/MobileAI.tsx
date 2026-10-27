import { useState } from 'react';
import { aiMessages } from '../../data/mock';
import { IconSend, IconMic, IconCamera, IconZap } from '../../components/Icons';

const quickReplies = ['¿Cómo está mi rodilla?', 'Ver rutina ajustada', '¿Cuándo me recupero?', 'Alternativas de pierna'];

export default function MobileAI() {
  const [messages, setMessages] = useState(aiMessages);
  const [input, setInput] = useState('');

  const sendMessage = (text: string) => {
    if (!text.trim()) return;
    const userMsg = { id: messages.length + 1, role: 'user', text };
    const aiResponse = {
      id: messages.length + 2, role: 'ai',
      text: 'Entendido. Basándome en tu lesión de rodilla derecha, te recomiendo mantener los ejercicios de bajo impacto por esta semana. ¿Quieres que ajuste toda tu rutina de piernas?',
    };
    setMessages(prev => [...prev, userMsg, aiResponse]);
    setInput('');
  };

  return (
    <div style={{ background: '#fff', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ background: 'var(--sidebar)', padding: '52px 16px 16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 38, height: 38, borderRadius: '50%', background: 'var(--neon)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <IconZap style={{ color: 'var(--sidebar)', width: 20, height: 20 }} />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-sora)', color: '#fff', fontWeight: 800, fontSize: 16 }}>Entrenador IA</div>
            <div style={{ color: 'var(--neon)', fontSize: 11, fontWeight: 600 }}>● En línea · Considerando lesión de rodilla</div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: 12, background: 'var(--bg)' }}>
        {messages.map(msg => (
          <div key={msg.id} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            alignItems: 'flex-end', gap: 8,
          }}>
            {msg.role === 'ai' && (
              <div style={{
                width: 28, height: 28, borderRadius: '50%', background: 'var(--neon)', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <IconZap style={{ color: 'var(--sidebar)', width: 14, height: 14 }} />
              </div>
            )}
            <div style={{
              maxWidth: '78%', padding: '10px 14px', borderRadius: msg.role === 'user' ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
              background: msg.role === 'user' ? 'var(--primary)' : '#fff',
              color: msg.role === 'user' ? '#fff' : 'var(--ink)',
              fontSize: 14, lineHeight: 1.5, fontWeight: 500,
              boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
            }}>
              {msg.text}
            </div>
          </div>
        ))}
      </div>

      {/* Quick replies */}
      <div style={{ padding: '10px 16px 6px', background: '#fff', display: 'flex', gap: 8, overflowX: 'auto' }}>
        {quickReplies.map(r => (
          <button key={r} onClick={() => sendMessage(r)} style={{
            whiteSpace: 'nowrap', padding: '6px 14px', borderRadius: 999,
            background: 'var(--bg)', border: '1.5px solid var(--border)',
            fontFamily: 'var(--font-manrope)', fontWeight: 600, fontSize: 12.5, color: 'var(--ink)',
            cursor: 'pointer', flexShrink: 0,
          }}>
            {r}
          </button>
        ))}
      </div>

      {/* Input */}
      <div style={{
        padding: '10px 16px 16px', background: '#fff', borderTop: '1px solid var(--border)',
        display: 'flex', gap: 8, alignItems: 'center',
      }}>
        <button style={{ padding: 8, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-2)' }}>
          <IconCamera style={{ width: 22, height: 22 }} />
        </button>
        <div style={{ flex: 1, position: 'relative' }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
            placeholder="Escribe un mensaje..."
            style={{
              width: '100%', height: 44, padding: '0 14px',
              border: '1.5px solid var(--border)', borderRadius: 22,
              fontFamily: 'var(--font-manrope)', fontSize: 14, outline: 'none', background: 'var(--bg)',
            }}
          />
        </div>
        <button style={{ padding: 8, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted-2)' }}>
          <IconMic style={{ width: 22, height: 22 }} />
        </button>
        <button onClick={() => sendMessage(input)} style={{
          width: 44, height: 44, borderRadius: '50%', background: 'var(--primary)', border: 'none', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
        }}>
          <IconSend style={{ color: '#fff', width: 18, height: 18 }} />
        </button>
      </div>
    </div>
  );
}
