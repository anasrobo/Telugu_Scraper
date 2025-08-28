import React, { useState, useEffect } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE || ''

export default function App() {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [url, setUrl] = useState('')
  const [uploadedFile, setUploadedFile] = useState(null)
  const [filePreview, setFilePreview] = useState('')
  const [rawText, setRawText] = useState('')
  const [cleanedText, setCleanedText] = useState('')
  const [scrapedHeadline, setScrapedHeadline] = useState('')
  const [theme, setTheme] = useState('light')

  useEffect(() => {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark' || saved === 'light') {
      setTheme(saved)
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      setTheme('dark')
    }
  }, [])

  useEffect(() => {
    localStorage.setItem('theme', theme)
    document.documentElement.classList.toggle('theme-dark', theme === 'dark')
  }, [theme])

  const toggleTheme = () => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'))
  }

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return

    setUploadedFile(file)
    const reader = new FileReader()
    reader.onload = (event) => {
      const text = event.target.result
      setRawText(text)
      // Show first 500 characters as preview
      setFilePreview(text.substring(0, 500) + (text.length > 500 ? '...' : ''))
    }
    reader.readAsText(file)
  }

  const handleScrape = async (e) => {
    e.preventDefault()
    setError('')
    setScrapedHeadline('')
    
    if (!url.trim()) {
      setError('Please paste a Telugu article URL')
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/scrape`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url })
      })
      
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'Scraping failed')
      }
      
      const data = await res.json()
      setRawText(data.text)
      
      // Extract headline from first line if it starts with "HEADLINE:"
      const lines = data.text.split('\n')
      const headlineLine = lines.find(line => line.startsWith('HEADLINE:'))
      if (headlineLine) {
        setScrapedHeadline(headlineLine.replace('HEADLINE:', '').trim())
      }
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCleanText = async () => {
    if (!rawText.trim()) {
      setError('No text to clean. Upload a file or scrape a URL first.')
      return
    }

    setLoading(true)
    setError('')
    
    try {
      const res = await fetch(`${API_BASE}/clean`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: rawText })
      })
      
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'Cleaning failed')
      }
      
      const data = await res.json()
      setCleanedText(data.cleaned)
      
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const downloadFile = (content, filename) => {
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="app">
      {/* Header Section */}
      <header className="header">
        <div className="header-bar">
          <div className="header-text">
            <h1 className="title">Telugu Data Cleaner</h1>
            <p className="subtitle">Scrape, clean, and prepare Telugu text datasets for AI models.</p>
          </div>
          <button
            type="button"
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {theme === 'dark' ? '☀�� Light' : '🌙 Dark'}
          </button>
        </div>
      </header>

      <div className="main-content">
        <div className="left-column">
          {/* Upload Section */}
          <section className="card upload-section">
            <h2 className="section-title">Upload .txt File</h2>
            <div className="upload-area">
              <input
                type="file"
                accept=".txt"
                onChange={handleFileUpload}
                className="file-input"
                id="file-upload"
              />
              <label htmlFor="file-upload" className="upload-button">
                Choose File
              </label>
              {uploadedFile && (
                <div className="file-info">
                  <p className="filename">📄 {uploadedFile.name}</p>
                  {filePreview && (
                    <div className="file-preview">
                      <h4>Preview:</h4>
                      <pre className="preview-text">{filePreview}</pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>

          {/* Link Scraper Section */}
          <section className="card scraper-section">
            <h2 className="section-title">Scrape Telugu Article</h2>
            <form onSubmit={handleScrape} className="scraper-form">
              <div className="input-group">
                <input
                  type="url"
                  placeholder="Paste Telugu news article link here..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="url-input"
                />
                <button 
                  type="submit" 
                  disabled={loading}
                  className="scrape-button"
                >
                  {loading ? 'Scraping...' : 'Scrape'}
                </button>
              </div>
            </form>
            
            {scrapedHeadline && (
              <div className="scraped-result">
                <h4>Extracted Headline:</h4>
                <p className="headline-text">{scrapedHeadline}</p>
              </div>
            )}
          </section>

          {/* Actions Section */}
          <section className="card actions-section">
            <h2 className="section-title">Actions</h2>
            <div className="action-buttons">
              <button 
                onClick={handleCleanText}
                disabled={loading || !rawText}
                className="action-button primary"
              >
                Clean Text
              </button>
              <button 
                onClick={() => downloadFile(cleanedText, 'cleaned_telugu.txt')}
                disabled={!cleanedText}
                className="action-button secondary"
              >
                Download Cleaned File
              </button>
              <button 
                onClick={() => downloadFile(rawText, 'raw_telugu.txt')}
                disabled={!rawText}
                className="action-button secondary"
              >
                Download Raw File
              </button>
            </div>
          </section>
        </div>

        {/* Output Section */}
        <div className="right-column">
          <section className="card output-section">
            <h2 className="section-title">Text Comparison</h2>
            <div className="text-panels">
              <div className="text-panel">
                <h3 className="panel-title">Raw Text</h3>
                <textarea
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Raw scraped text will appear here..."
                  className="text-area raw-text"
                />
              </div>
              <div className="text-panel">
                <h3 className="panel-title">Cleaned Text</h3>
                <textarea
                  value={cleanedText}
                  readOnly
                  placeholder="Cleaned text will appear here after processing..."
                  className="text-area cleaned-text"
                />
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}
    </div>
  )
}
