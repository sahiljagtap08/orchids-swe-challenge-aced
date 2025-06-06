'use client'

import { useState, useEffect, Fragment } from 'react'
import { ChevronDownIcon, XMarkIcon, CodeBracketIcon, EyeIcon } from '@heroicons/react/24/outline'
import { Panel, PanelGroup, PanelResizeHandle } from "react-resizable-panels";
import { apiClient, CloneJobResponse, PageCloneResult } from '@/lib/api'
import { PlaceholdersAndVanishInput } from '@/components/ui/placeholders-and-vanish-input'
import { SparklesCore } from '@/components/ui/sparkles'
import { Checkbox } from '@/components/ui/checkbox'
import { Sidebar, SidebarBody } from '@/components/ui/sidebar'
import { IconFileText, IconProgress, IconX, IconPhoto } from '@tabler/icons-react'
import { LiveLogView } from '@/components/LiveLogView';

// Simple syntax highlighter for the live code view
const SimpleCodeViewer = ({ code }: { code: string }) => {
  return (
    <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono p-4">
      <code dangerouslySetInnerHTML={{ __html: code.replace(/</g, "&lt;").replace(/>/g, "&gt;") }} />
    </pre>
  );
};

export default function Home() {
  const [url, setUrl] = useState('https://jagtap.tech')
  const [selectedModel, setSelectedModel] = useState('agentic')
  const [isDropdownOpen, setIsDropdownOpen] = useState(false)
  const [currentJob, setCurrentJob] = useState<CloneJobResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // Full site cloning options
  const [fullSite, setFullSite] = useState(false)
  const [maxPages, setMaxPages] = useState(10)
  const [includeAssets, setIncludeAssets] = useState(true)

  // Live logs
  const [logs, setLogs] = useState<string[]>([])
  const [liveCode, setLiveCode] = useState<string>("")
  const [logSource, setLogSource] = useState<EventSource | null>(null)
  
  // New UI State
  const [selectedPage, setSelectedPage] = useState<PageCloneResult | null>(null)
  const [activeView, setActiveView] = useState<'preview' | 'code' | 'original'>('preview');
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [isAiCloning, setIsAiCloning] = useState(false);

  const models = [
    { id: 'agentic', name: 'Agentic', description: 'Claude 3.5 Sonnet', icon: '🧠' },
    { id: 'fast', name: 'Fast', description: 'GPT-4o', icon: '⚡' },
    { id: 'precise', name: 'Precise', description: 'Gemini 2.0 Pro', icon: '🎯' },
    { id: 'economic', name: 'Economic', description: 'GPT-4o Mini', icon: '💰' }
  ]
  
  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setUrl(e.target.value);
  };

  const handleStreamedMessage = (message: string) => {
    if (message.startsWith('CODE:')) {
      if (!isAiCloning) setIsAiCloning(true);
      const codePart = message.substring(5);
      setLiveCode(prev => prev + codePart);
    } else {
      setLogs(prev => [...prev, message]);
    }
  }

  const startCloningJob = async (urlToClone: string) => {
    setError(null)
    setCurrentJob(null)
    setSelectedPage(null)
    setLogs([])
    setLiveCode("")
    if (logSource) logSource.close()
    setActiveView('preview');
    setIsAiCloning(false);

    try {
      const job = await apiClient.createCloneJob({
        url: urlToClone, model: selectedModel, full_site: fullSite,
        max_pages: maxPages, include_assets: includeAssets
      })
      setCurrentJob(job)

      apiClient.pollCloneJob(job.job_id, (updatedJob) => {
        setCurrentJob(updatedJob)
        if (updatedJob.status === 'completed' && updatedJob.full_site_result?.pages?.[0]) {
          setSelectedPage(updatedJob.full_site_result.pages[0])
          if (!sidebarOpen) setSidebarOpen(true)
        } else if (updatedJob.status === 'completed' && updatedJob.result) {
           if (!isAiCloning) setIsAiCloning(true); // Ensure panels are shown for single-page results
           setLiveCode(updatedJob.result.html)
           if (!sidebarOpen) setSidebarOpen(true)
        }
      })

      const newLogSource = apiClient.getLogsStream(
        job.job_id, 
        handleStreamedMessage,
        () => apiClient.getCloneJob(job.job_id).then(job => setCurrentJob(job))
      )
      setLogSource(newLogSource)

    } catch (error: unknown) {
      setError(error instanceof Error ? error.message : 'An unknown error occurred')
    }
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    let processedUrl = url.trim();
    if (!processedUrl) return;

    // Automatically prepend https:// if no protocol is specified
    if (!/^(https?:)?\/\//i.test(processedUrl)) {
      processedUrl = `https://${processedUrl}`;
      setUrl(processedUrl); // Update state to reflect change in UI
    }
    
    if (isLoading) return;
    
    setTimeout(() => {
      // Use the processed URL for the cloning job
      startCloningJob(processedUrl);
    }, 1200);
  }

  const isLoading = currentJob && !['completed', 'failed'].includes(currentJob.status)

  const finalHtml = selectedPage?.html || liveCode
  const finalUrl = selectedPage?.url || currentJob?.url

  // If there's a job, don't show the initial hero content.
  if (currentJob) {
    return (
       <div className="flex h-screen w-full bg-neutral-900 text-white font-sans">
        <PanelGroup direction="horizontal">
          <Panel defaultSize={30} minSize={20} collapsible onCollapse={() => setSidebarOpen(false)} onExpand={() => setSidebarOpen(true)}>
            <Sidebar open={sidebarOpen} setOpen={setSidebarOpen}>
              <SidebarBody className="bg-neutral-800 border-r border-neutral-700 text-white p-5 flex flex-col h-full">
                  <div className="flex-shrink-0">
                      <h1 className="text-xl font-bold">PetalClone</h1>
                      <p className="text-xs text-neutral-400">Cloning: {currentJob.url}</p>
                  </div>
                  
                  {currentJob.full_site_result && currentJob.full_site_result.pages.length > 0 && (
                    <div className="flex flex-col gap-4 pt-4 mt-4 border-t border-neutral-700">
                       <h3 className="text-sm font-semibold text-neutral-300 flex items-center gap-2">
                          <IconFileText size={16}/>
                          Cloned Pages
                      </h3>
                       <ul className="space-y-1.5 overflow-y-auto">
                        {currentJob.full_site_result.pages.map(page => (
                          <li key={page.url}>
                            <button 
                              onClick={() => setSelectedPage(page)}
                              className={`w-full text-left text-xs p-2.5 rounded-md transition-colors ${selectedPage?.url === page.url ? 'bg-blue-600/30' : 'hover:bg-neutral-700/50'}`}
                            >
                              <p className="font-medium truncate text-neutral-200">{page.metadata?.title || page.path}</p>
                              <p className="text-xs text-neutral-400 truncate">{page.path}</p>
                            </button>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  
                  <div className="flex flex-col gap-4 flex-1 min-h-0 pt-4 mt-4 border-t border-neutral-700">
                      <h2 className="text-sm font-semibold text-neutral-300 flex items-center gap-2">
                        <IconProgress size={16} />
                        Live Progress
                    </h2>
                      <LiveLogView logs={logs} isActive={!!isLoading} />
                  </div>

                  <div className="flex-shrink-0 flex flex-col gap-3 pt-5 border-t border-neutral-700">
                      <button
                        onClick={() => {
                          setCurrentJob(null);
                          if (logSource) logSource.close();
                        }}
                        className="w-full px-4 py-2 bg-neutral-700 hover:bg-neutral-600 text-white text-sm font-medium rounded-md transition-colors"
                      >
                        New Clone
                      </button>
                      <div className="flex items-center gap-2">
                        {currentJob.status === 'completed' ? (
                          <button
                            onClick={() => window.open(apiClient.getDownloadUrl(currentJob.job_id), '_blank')}
                            className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-md transition-colors"
                          >
                            Download Results
                          </button>
                        ) : <div className="w-full" />}
                       </div>
                  </div>
              </SidebarBody>
            </Sidebar>
          </Panel>
          <PanelResizeHandle className="w-1 bg-neutral-700/50 hover:bg-neutral-700 transition-colors" />
          <Panel>
            <main className="flex-1 flex flex-col bg-neutral-900 overflow-hidden h-full">
              <header className="flex items-center justify-between p-3 border-b border-neutral-700 shrink-0 bg-neutral-800">
                 <div className="text-sm font-medium text-neutral-500">
                  {finalUrl}
                 </div>
                 <div className="flex items-center space-x-2 text-sm">
                   <span className={`py-1 px-3 rounded-md text-xs font-medium ${currentJob.status === 'completed' ? 'bg-green-900/50 text-green-300' : currentJob.status === 'failed' ? 'bg-red-900/50 text-red-300' : 'bg-blue-900/50 text-blue-300'}`}>
                    {currentJob.status.toUpperCase()}
                  </span>
                    <button onClick={() => setActiveView('original')} className={`px-3 py-1 text-xs rounded-md flex items-center gap-1.5 ${activeView === 'original' ? 'bg-neutral-600' : 'bg-neutral-700 hover:bg-neutral-600'}`}>
                      <IconPhoto className="w-4 h-4" /> Original
                    </button>
                    <button onClick={() => setActiveView('preview')} className={`px-3 py-1 text-xs rounded-md flex items-center gap-1.5 ${activeView === 'preview' ? 'bg-neutral-600' : 'bg-neutral-700 hover:bg-neutral-600'}`}>
                      <EyeIcon className="w-4 h-4" /> Preview
                    </button>
                    <button onClick={() => setActiveView('code')} className={`px-3 py-1 text-xs rounded-md flex items-center gap-1.5 ${activeView === 'code' ? 'bg-neutral-600' : 'bg-neutral-700 hover:bg-neutral-600'}`}>
                      <CodeBracketIcon className="w-4 h-4" /> Code
                    </button>
                </div>
              </header>
              
              <div className="flex-1 p-4 overflow-auto">
                {activeView === 'preview' && (
                  <div className="bg-black border-m border-neutral-700 rounded-lg flex flex-col h-full">
                    <div className="p-2 border-b border-neutral-700 text-xs font-medium text-neutral-300 bg-neutral-800 rounded-t-lg">Preview</div>
                    <div className="flex-grow bg-white">
                      <iframe srcDoc={finalHtml} className="w-full h-full" title="AI Clone" sandbox="allow-scripts allow-same-origin" />
                    </div>
                  </div>
                )}
                {activeView === 'code' && (
                  <div className="bg-black border border-neutral-700 rounded-lg flex flex-col h-full">
                    <div className="p-2 border-b border-neutral-700 text-xs font-medium text-neutral-300 bg-neutral-800 rounded-t-lg">Code</div>
                    <div className="flex-grow overflow-auto bg-neutral-800/50">
                      <SimpleCodeViewer code={finalHtml || "Generating code..."} />
                    </div>
                  </div>
                )}
                {activeView === 'original' && (
                  <div className="bg-black border border-neutral-700 rounded-lg flex flex-col h-full">
                    <div className="p-2 border-b border-neutral-700 text-xs font-medium text-neutral-300 bg-neutral-800 rounded-t-lg">Original</div>
                    <div className="flex-grow bg-grid-gray-700/[0.2] p-4 flex items-center justify-center">
                      {selectedPage?.screenshot ? (
                        <img 
                          src={`data:image/png;base64,${selectedPage.screenshot}`} 
                          alt="Original website screenshot" 
                          className="max-w-full max-h-full object-contain mx-auto shadow-2xl" 
                        />
                      ) : (
                        <div className="text-center text-neutral-400">
                          <IconPhoto size={48} className="mx-auto mb-4 text-neutral-600" />
                          <p className="mb-4">A screenshot is not available for this page.</p>
                          {currentJob?.url && (
                            <a
                              href={currentJob.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md transition-colors"
                            >
                              Open Original Site in New Tab
                            </a>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

            </main>
          </Panel>
        </PanelGroup>
      </div>
    );
  }

  // Initial page view
  return (
    <div className="min-h-screen bg-black text-white">
      <header className="flex items-center justify-between p-6">
        <h1 className="text-2xl font-bold">🌸 PetalClone</h1>
        <span className="text-sm text-gray-400">Orchids SWE Challenge</span>
      </header>

      <main className="container mx-auto px-6 py-20">
        <div className="text-center max-w-4xl mx-auto">
          <div className="h-40 relative w-full flex flex-col items-center justify-center overflow-hidden rounded-md">
            <div className="w-full absolute inset-0 h-screen">
              <SparklesCore
                id="tsparticlesfullpage"
                background="transparent"
                minSize={0.6}
                maxSize={1.4}
                particleDensity={100}
                className="w-full h-full"
                particleColor="#FFFFFF"
              />
            </div>
            <h1 className="md:text-7xl text-3xl lg:text-6xl font-bold text-center text-white relative z-20">
            🌸 PetalClone
            </h1>
          </div>

          <p className="text-xl text-gray-400 mb-12">
            AI-powered website cloning with agentic architecture
          </p>

          <div className="max-w-xl mx-auto">
            <div className="relative flex items-center">
              <PlaceholdersAndVanishInput
                placeholders={[
                  "google.com",
                  "github.com",
                  "jagtap.tech",
                  "Enter any website to clone...",
                ]}
                onChange={handleUrlChange}
                onSubmit={handleSubmit}
              />
              <div className="absolute right-14 top-1/2 transform -translate-y-1/2 z-[60]">
                <div className="relative">
                    <button
                      type="button"
                      onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                      className="flex items-center space-x-2 px-3 py-1.5 text-xs bg-neutral-800 hover:bg-neutral-700 rounded-full transition-colors focus:outline-none"
                      disabled={!!isLoading}
                    >
                      <span>{models.find(m => m.id === selectedModel)?.icon}</span>
                      <span className="hidden sm:inline">{models.find(m => m.id === selectedModel)?.name}</span>
                      <ChevronDownIcon className="w-3 h-3 text-gray-400" />
                    </button>

                    {isDropdownOpen && (
                      <div
                        className="absolute right-0 bottom-full mb-2 w-64 bg-neutral-900 border border-neutral-700 rounded-xl shadow-xl z-50 overflow-hidden"
                        onMouseLeave={() => setIsDropdownOpen(false)}
                      >
                        {models.map((model) => (
                          <button
                            key={model.id}
                            onClick={() => { setSelectedModel(model.id); setIsDropdownOpen(false); }}
                            className="w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-neutral-800 first:rounded-t-xl last:rounded-b-xl transition-colors"
                          >
                            <span className="text-lg">{model.icon}</span>
                            <div>
                              <div className="font-medium">{model.name}</div>
                              <div className="text-sm text-neutral-400">{model.description}</div>
                            </div>
                            {selectedModel === model.id && <div className="ml-auto w-2 h-2 bg-blue-500 rounded-full"></div>}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
              </div>
            </div>

            <div className="mt-8 flex items-center justify-center space-x-8 text-sm">
              <div className="flex items-center space-x-2">
                <Checkbox 
                  id="full-site-check"
                  checked={fullSite} 
                  onCheckedChange={(checked) => setFullSite(!!checked)}
                  disabled={!!isLoading}
                />
                <label
                  htmlFor="full-site-check"
                  className="text-gray-300 cursor-pointer"
                >
                  Clone entire website
                </label>
              </div>
              {fullSite && (
                <Fragment>
                  <div className="flex items-center space-x-2">
                    <label className="text-gray-400">Max pages:</label>
                    <select value={maxPages} onChange={(e) => setMaxPages(parseInt(e.target.value))} className="bg-gray-800 border border-gray-700 rounded-md px-2 py-1 text-white text-sm focus:ring-blue-500 focus:border-blue-500" disabled={!!isLoading}>
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={20}>20</option>
                      <option value={50}>50</option>
                    </select>
                  </div>
                </Fragment>
              )}
            </div>
          </div>

          {error && (
            <div className="mt-6 max-w-md mx-auto bg-red-900/20 border border-red-800 rounded-xl p-4">
              <div className="flex items-center space-x-2"><span className="text-red-400">❌</span><span className="text-red-300 text-sm">{error}</span></div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
