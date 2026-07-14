'use client';

/**
 * frontend/app/vibe-coding/page.tsx — Interface de Vibe Coding Premium d'Antigravity
 */
import React, { useState, useEffect, useRef } from 'react';
import Editor, { Monaco } from '@monaco-editor/react';

export default function VibeCodingPage() {
  const [htmlCode, setHtmlCode] = useState<string>('<h3>Bienvenue sur EcoDim Pro SaaS</h3>\n<p id="message">Calculateur en cours d\'initialisation...</p>');
  const [jsCode, setJsCode] = useState<string>('// Exemple de script exécuté dans la sandbox\ndocument.getElementById("message").textContent = "Moteur de calcul connecté via SDK !";');
  const [cssCode, setCssCode] = useState<string>('body { font-family: sans-serif; padding: 20px; }\n#message { color: #E8A33D; font-weight: bold; }');
  
  const [activeTab, setActiveTab] = useState<'html' | 'css' | 'js'>('html');
  const [sandboxError, setSandboxError] = useState<string | null>(null);
  const [buildSuccess, setBuildSuccess] = useState<boolean>(true);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  const iframeRef = useRef<HTMLIFrameElement>(null);

  // Écouter les messages provenant de la sandbox (ex: erreurs d'exécution)
  useEffect(() => {
    const handleSandboxMessage = (event: MessageEvent) => {
      const data = event.data;
      if (data.type === 'runtime-error') {
        setSandboxError(`[Erreur ligne ${data.line}] : ${data.message}`);
        setBuildSuccess(false);
      } else if (data.type === 'promise-error') {
        setSandboxError(`[Promesse rejetée] : ${data.message}`);
        setBuildSuccess(false);
      } else if (data.type === 'execution-success') {
        setSandboxError(null);
        setBuildSuccess(true);
      }
    };

    window.addEventListener('message', handleSandboxMessage);
    return () => window.removeEventListener('message', handleSandboxMessage);
  }, []);

  // Mettre à jour la sandbox (Hot-Reload) lors d'un changement de code
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (iframeRef.current && iframeRef.current.contentWindow) {
        iframeRef.current.contentWindow.postMessage(
          {
            type: 'execute-code',
            html: htmlCode,
            css: cssCode,
            js: jsCode
          },
          '*'
        );
      }
    }, 250); // Debounce de 250ms pour optimiser les performances d'exécution

    return () => clearTimeout(timeoutId);
  }, [htmlCode, cssCode, jsCode]);

  const handleEditorChange = (value: string | undefined) => {
    if (!value) return;
    if (activeTab === 'html') setHtmlCode(value);
    if (activeTab === 'css') setCssCode(value);
    if (activeTab === 'js') setJsCode(value);
  };

  const getActiveCode = () => {
    if (activeTab === 'html') return htmlCode;
    if (activeTab === 'css') return cssCode;
    return jsCode;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: theme === 'dark' ? '#1E293B' : '#F8FAFC' }}>
      
      {/* --- HEADER --- */}
      <header style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center', 
        padding: '12px 24px', 
        borderBottom: '1px solid #E2E8F0',
        backgroundColor: '#FFFFFF',
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '20px', fontWeight: 'bold', color: '#1E293B' }}>💡 Antigravity Vibe Coding</span>
          <span style={{ 
            fontSize: '11px', 
            padding: '2px 8px', 
            borderRadius: '12px', 
            backgroundColor: buildSuccess ? '#DEF7EC' : '#FDE8E8',
            color: buildSuccess ? '#03543F' : '#9B1C1C',
            fontWeight: 'bold'
          }}>
            {buildSuccess ? '● Build Réussi' : '● Erreur de compilation'}
          </span>
        </div>
        
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')} style={{ 
            padding: '6px 12px', 
            borderRadius: '6px', 
            border: '1px solid #CBD5E1', 
            cursor: 'pointer',
            backgroundColor: '#FFF'
          }}>
            {theme === 'light' ? '🌙 Mode Sombre' : '☀️ Mode Clair'}
          </button>
        </div>
      </header>

      {/* --- ESPACE DE TRAVAIL --- */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Colonne gauche : Éditeur de code */}
        <div style={{ width: '50%', display: 'flex', flexDirection: 'column', borderRight: '1px solid #E2E8F0' }}>
          {/* Navigation des onglets Monaco */}
          <div style={{ display: 'flex', backgroundColor: '#F1F5F9', borderBottom: '1px solid #E2E8F0' }}>
            <button 
              onClick={() => setActiveTab('html')} 
              style={{ padding: '10px 20px', border: 'none', cursor: 'pointer', backgroundColor: activeTab === 'html' ? '#FFF' : 'transparent', fontWeight: activeTab === 'html' ? 'bold' : 'normal' }}
            >
              📄 Index.html
            </button>
            <button 
              onClick={() => setActiveTab('css')} 
              style={{ padding: '10px 20px', border: 'none', cursor: 'pointer', backgroundColor: activeTab === 'css' ? '#FFF' : 'transparent', fontWeight: activeTab === 'css' ? 'bold' : 'normal' }}
            >
              🎨 Style.css
            </button>
            <button 
              onClick={() => setActiveTab('js')} 
              style={{ padding: '10px 20px', border: 'none', cursor: 'pointer', backgroundColor: activeTab === 'js' ? '#FFF' : 'transparent', fontWeight: activeTab === 'js' ? 'bold' : 'normal' }}
            >
              ⚡ Script.js
            </button>
          </div>

          {/* Monaco Editor */}
          <div style={{ flex: 1 }}>
            <Editor
              height="100%"
              language={activeTab === 'js' ? 'javascript' : activeTab}
              theme={theme === 'dark' ? 'vs-dark' : 'light'}
              value={getActiveCode()}
              onChange={handleEditorChange}
              options={{
                minimap: { enabled: false },
                fontSize: 14,
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
              }}
            />
          </div>
          
          {/* Console d'erreurs en bas de l'éditeur */}
          {sandboxError && (
            <div style={{ 
              padding: '12px 16px', 
              backgroundColor: '#FDF2F2', 
              borderTop: '1px solid #FDE8E8', 
              color: '#B91C1C', 
              fontFamily: 'monospace',
              fontSize: '12px',
              maxHeight: '120px',
              overflowY: 'auto'
            }}>
              {sandboxError}
            </div>
          )}
        </div>

        {/* Colonne droite : Live Preview (Iframe Sandbox) */}
        <div style={{ width: '50%', backgroundColor: '#FFF', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '8px 16px', backgroundColor: '#F1F5F9', borderBottom: '1px solid #E2E8F0', fontSize: '12px', color: '#64748B', display: 'flex', justifyContent: 'space-between' }}>
            <span>📺 Aperçu en direct (Iframe isolée)</span>
            <span>temps de rendu &lt; 300ms</span>
          </div>
          <iframe
            ref={iframeRef}
            src="/sandbox.html"
            sandbox="allow-scripts"
            style={{ flex: 1, border: 'none', width: '100%', height: '100%', backgroundColor: '#FFFFFF' }}
          />
        </div>

      </div>
    </div>
  );
}
