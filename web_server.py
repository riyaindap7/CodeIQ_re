# web_server.py (Updated)
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvicorn
import json
import os
import re
import hashlib
from typing import Dict, Any
import webbrowser
import threading
import time
import asyncio

class GraphVisualizationServer:
    def __init__(self, navigator_module, host: str = "localhost", port: int = 8000):
        self.navigator = navigator_module
        self.host = host
        self.port = port
        self.app = FastAPI(title="CodeIQ Navigator", 
                          description="Graph Visualization API")
        
        # Track current analysis state
        self.current_analysis = None
        self.analysis_in_progress = False
        
        # Create static directory for visualizations
        self.static_dir = "static"
        os.makedirs(self.static_dir, exist_ok=True)
        self.app.mount("/static", StaticFiles(directory=self.static_dir), name="static")
        
        # Create templates directory
        self.templates_dir = "templates"
        os.makedirs(self.templates_dir, exist_ok=True)
        self.templates = Jinja2Templates(directory=self.templates_dir)
        
        self._setup_routes()
        self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default HTML templates if they don't exist"""
        index_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CodeIQ Navigator</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #007acc;
            padding-bottom: 15px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #007acc;
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card h3 {
            margin: 0;
            font-size: 2em;
        }
        .stat-card p {
            margin: 5px 0 0 0;
        }
        .section {
            margin-bottom: 30px;
        }
        .section h2 {
            color: #007acc;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        .file-list {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .file-item {
            padding: 10px;
            border-bottom: 1px solid #eee;
            cursor: pointer;
        }
        .file-item:hover {
            background-color: #f0f0f0;
        }
        .graph-links {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .btn {
            background: #007acc;
            color: white;
            padding: 10px 15px;
            text-decoration: none;
            border-radius: 4px;
            display: inline-block;
        }
        .btn:hover {
            background: #005a9e;
        }
        .btn:disabled {
            background: #cccccc;
            cursor: not-allowed;
        }
        .loading {
            display: none;
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            margin: 20px 0;
        }
        .analysis-form {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        .form-group input {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        .form-group button {
            background: #28a745;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .form-group button:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .form-group button:hover:not(:disabled) {
            background: #218838;
        }
        .error-message {
            background: #f8d7da;
            color: #721c24;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            display: none;
        }
        .success-message {
            background: #d1edff;
            color: #0c5460;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            display: none;
        }
        .no-data {
            text-align: center;
            padding: 40px;
            color: #6c757d;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>CodeIQ Navigator</h1>
            <p>Automated Code Analysis and Visualization</p>
        </div>

        <div class="analysis-form">
            <h2>Analyze Repository</h2>
            <div id="errorMessage" class="error-message"></div>
            <div id="successMessage" class="success-message"></div>
            <div class="form-group">
                <label for="repoUrl">GitHub Repository URL:</label>
                <input type="text" id="repoUrl" placeholder="https://github.com/username/repository.git" value="">
            </div>
            <div class="form-group">
                <button id="analyzeBtn" onclick="analyzeRepository()">Analyze Repository</button>
                <button id="clearBtn" onclick="clearAnalysis()" style="background: #dc3545; margin-left: 10px;">Clear Analysis</button>
            </div>
        </div>

        <div id="loading" class="loading">
            <h3>🔄 Analyzing repository...</h3>
            <p>This may take a few minutes depending on the repository size.</p>
            <p>Please don't close this window.</p>
        </div>

        <div id="noAnalysis" class="no-data" style="display: block;">
            <h3>No Analysis Data</h3>
            <p>Enter a GitHub repository URL above to start analysis.</p>
        </div>

        <div id="analysisResults" style="display: none;">
            <div class="section">
                <h2>Repository Analysis Summary</h2>
                <div class="stats-grid" id="statsGrid">
                    <!-- Stats will be populated by JavaScript -->
                </div>
            </div>

            <div class="section">
                <h2>Graph Visualizations</h2>
                <div class="graph-links">
                    <a href="/visualize/hpg" class="btn" target="_blank">View HPG (Hierarchical Program Graph)</a>
                    <a href="/api/hpg" class="btn" target="_blank">HPG JSON Data</a>
                </div>
            </div>

            <div class="section">
                <h2>Control Flow Graphs</h2>
                <div id="cfgsList" class="graph-links">
                    <!-- CFG links will be populated by JavaScript -->
                </div>
            </div>

            <div class="section">
                <h2>Program Dependency Graphs</h2>
                <div id="pdgsList" class="graph-links">
                    <!-- PDG links will be populated by JavaScript -->
                </div>
            </div>

            <div class="section">
                <h2>Repository Files</h2>
                <div class="file-list" id="filesList">
                    <!-- Files will be populated by JavaScript -->
                </div>
            </div>
        </div>
    </div>

    <script>
        let currentAnalysisTimestamp = null;

        function showMessage(elementId, message) {
            const element = document.getElementById(elementId);
            element.textContent = message;
            element.style.display = 'block';
            setTimeout(() => {
                element.style.display = 'none';
            }, 5000);
        }

        function setLoading(loading) {
            const analyzeBtn = document.getElementById('analyzeBtn');
            const clearBtn = document.getElementById('clearBtn');
            const loadingDiv = document.getElementById('loading');
            const resultsDiv = document.getElementById('analysisResults');
            const noAnalysisDiv = document.getElementById('noAnalysis');

            analyzeBtn.disabled = loading;
            clearBtn.disabled = loading;
            loadingDiv.style.display = loading ? 'block' : 'none';
            
            if (!loading && currentAnalysisTimestamp) {
                resultsDiv.style.display = 'block';
                noAnalysisDiv.style.display = 'none';
            } else if (!loading) {
                resultsDiv.style.display = 'none';
                noAnalysisDiv.style.display = 'block';
            }
        }

        async function analyzeRepository() {
            const repoUrl = document.getElementById('repoUrl').value.trim();
            
            if (!repoUrl) {
                showMessage('errorMessage', 'Please enter a repository URL');
                return;
            }

            setLoading(true);
            showMessage('successMessage', 'Analysis started...');
            
            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ repo_url: repoUrl })
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Analysis failed');
                }
                
                const data = await response.json();
                currentAnalysisTimestamp = data.repository_analysis.analysis_timestamp;
                displayAnalysisResults(data);
                showMessage('successMessage', 'Analysis completed successfully!');
                
            } catch (error) {
                console.error('Analysis error:', error);
                showMessage('errorMessage', 'Error analyzing repository: ' + error.message);
            } finally {
                setLoading(false);
            }
        }

        async function clearAnalysis() {
            try {
                const response = await fetch('/api/clear', {
                    method: 'POST'
                });
                
                if (response.ok) {
                    currentAnalysisTimestamp = null;
                    document.getElementById('analysisResults').style.display = 'none';
                    document.getElementById('noAnalysis').style.display = 'block';
                    document.getElementById('repoUrl').value = '';
                    showMessage('successMessage', 'Analysis cleared successfully');
                }
            } catch (error) {
                showMessage('errorMessage', 'Error clearing analysis: ' + error.message);
            }
        }
        
        function displayAnalysisResults(data) {
            // Update stats grid
            const stats = data.repository_analysis;
            document.getElementById('statsGrid').innerHTML = `
                <div class="stat-card">
                    <h3>${stats.total_files}</h3>
                    <p>Files</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.total_functions}</h3>
                    <p>Functions</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.total_classes}</h3>
                    <p>Classes</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.hpg_nodes}</h3>
                    <p>HPG Nodes</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.hpg_edges}</h3>
                    <p>HPG Edges</p>
                </div>
                <div class="stat-card">
                    <h3>${stats.cfgs_built}</h3>
                    <p>CFGs Built</p>
                </div>
            `;
            
            // Load additional data
            loadCFGs();
            loadPDGs();
            loadFiles();
        }
        
        async function loadCFGs() {
            try {
                const response = await fetch('/api/cfgs');
                const data = await response.json();
                
                const cfgsList = document.getElementById('cfgsList');
                cfgsList.innerHTML = '';
                
                if (Object.keys(data).length === 0) {
                    cfgsList.innerHTML = '<p>No CFGs available</p>';
                    return;
                }
                
                for (const [cfgId, cfgData] of Object.entries(data)) {
                    const link = document.createElement('a');
                    link.href = `/visualize/cfg/${encodeURIComponent(cfgId)}`;
                    link.className = 'btn';
                    link.target = '_blank';
                    link.textContent = `View CFG: ${cfgId.split('_').pop()}`;
                    cfgsList.appendChild(link);
                }
            } catch (error) {
                console.error('Error loading CFGs:', error);
                document.getElementById('cfgsList').innerHTML = '<p>Error loading CFGs</p>';
            }
        }
        
        async function loadPDGs() {
            try {
                const response = await fetch('/api/pdgs');
                const data = await response.json();
                
                const pdgsList = document.getElementById('pdgsList');
                pdgsList.innerHTML = '';
                
                if (Object.keys(data).length === 0) {
                    pdgsList.innerHTML = '<p>No PDGs available</p>';
                    return;
                }
                
                for (const [pdgId, pdgData] of Object.entries(data)) {
                    const link = document.createElement('a');
                    link.href = `/visualize/pdg/${encodeURIComponent(pdgId)}`;
                    link.className = 'btn';
                    link.target = '_blank';
                    link.textContent = `View PDG: ${pdgId.split('_').pop()}`;
                    pdgsList.appendChild(link);
                }
            } catch (error) {
                console.error('Error loading PDGs:', error);
                document.getElementById('pdgsList').innerHTML = '<p>Error loading PDGs</p>';
            }
        }
        
        async function loadFiles() {
            try {
                const response = await fetch('/api/files');
                const data = await response.json();
                
                const filesList = document.getElementById('filesList');
                filesList.innerHTML = '';
                
                if (!data.files || data.files.length === 0) {
                    filesList.innerHTML = '<p>No files analyzed</p>';
                    return;
                }
                
                data.files.forEach(file => {
                    const fileItem = document.createElement('div');
                    fileItem.className = 'file-item';
                    fileItem.textContent = file;
                    fileItem.onclick = () => viewFileAST(file);
                    filesList.appendChild(fileItem);
                });
            } catch (error) {
                console.error('Error loading files:', error);
                document.getElementById('filesList').innerHTML = '<p>Error loading files</p>';
            }
        }
        
        function viewFileAST(filePath) {
            window.open(`/api/ast/${encodeURIComponent(filePath)}`, '_blank');
        }
        
        // Check for existing analysis on page load
        window.addEventListener('load', async () => {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                if (data.has_analysis) {
                    // Load existing analysis
                    const analysisResponse = await fetch('/api/analysis');
                    const analysisData = await analysisResponse.json();
                    currentAnalysisTimestamp = analysisData.repository_analysis.analysis_timestamp;
                    displayAnalysisResults(analysisData);
                    document.getElementById('analysisResults').style.display = 'block';
                    document.getElementById('noAnalysis').style.display = 'none';
                }
            } catch (error) {
                console.log('No existing analysis found');
            }
        });
    </script>
</body>
</html>"""
        
        index_path = os.path.join(self.templates_dir, "index.html")
        
        # Ensure UTF-8 encoding on Windows so characters like emoji don't raise
        # UnicodeEncodeError when writing files.
        with open(index_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(index_html)
    
    def _setup_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def home(request: Request):
            return self.templates.TemplateResponse("index.html", {"request": request})
        
        @self.app.get("/api/analysis")
        async def get_analysis():
            if not self.navigator.hpg:
                raise HTTPException(status_code=404, detail="No analysis available. Please analyze a repository first.")
            
            report = self.navigator._generate_analysis_report()
            return JSONResponse(content=report)
        
        @self.app.post("/api/clear")
        async def clear_analysis():
            self.navigator.clear_analysis()
            self.current_analysis = None
            return {"message": "Analysis cleared successfully"}
        
        @self.app.get("/api/status")
        async def get_status():
            status = self.navigator.get_analysis_status()
            return JSONResponse(content=status)
        
        @self.app.get("/api/hpg")
        async def get_hpg():
            if not self.navigator.hpg:
                raise HTTPException(status_code=404, detail="HPG not built yet")
            
            # Convert HPG to JSON-serializable format
            hpg_data = {
                "nodes": [
                    {**data, "id": node_id} 
                    for node_id, data in self.navigator.hpg.nodes(data=True)
                ],
                "edges": [
                    {"source": source, "target": target, **data}
                    for source, target, data in self.navigator.hpg.edges(data=True)
                ]
            }
            return JSONResponse(content=hpg_data)
        
        @self.app.get("/api/cfgs")
        async def get_cfgs():
            if not self.navigator.cfgs:
                return JSONResponse(content={})
            
            cfgs_data = {}
            for cfg_id, cfg in self.navigator.cfgs.items():
                cfgs_data[cfg_id] = {
                    "nodes": [
                        {**data, "id": node_id} 
                        for node_id, data in cfg.nodes(data=True)
                    ],
                    "edges": [
                        {"source": source, "target": target, **data}
                        for source, target, data in cfg.edges(data=True)
                    ]
                }
            return JSONResponse(content=cfgs_data)
        
        @self.app.get("/api/pdgs")
        async def get_pdgs():
            if not self.navigator.pdgs:
                return JSONResponse(content={})
            
            pdgs_data = {}
            for pdg_id, pdg in self.navigator.pdgs.items():
                pdgs_data[pdg_id] = {
                    "nodes": [
                        {**data, "id": node_id} 
                        for node_id, data in pdg.nodes(data=True)
                    ],
                    "edges": [
                        {"source": source, "target": target, **data}
                        for source, target, data in pdg.edges(data=True)
                    ]
                }
            return JSONResponse(content=pdgs_data)
        
        @self.app.get("/api/ast/{file_path:path}")
        async def get_ast(file_path: str):
            ast_node = self.navigator.ast_cache.get(file_path)
            if not ast_node:
                raise HTTPException(status_code=404, detail=f"AST not found for file: {file_path}")
            
            return JSONResponse(content=ast_node.dict())
        
        @self.app.get("/api/files")
        async def get_files():
            files = list(self.navigator.ast_cache.keys())
            return JSONResponse(content={"files": files})
        
        @self.app.get("/visualize/hpg")
        async def visualize_hpg():
            if not self.navigator.hpg:
                raise HTTPException(status_code=404, detail="HPG not built yet")
            
            output_path = os.path.join(self.static_dir, "hpg_visualization.html")
            self.navigator.visualize_hpg(output_path)
            
            return HTMLResponse(content=f"""
                <html>
                    <body>
                        <h1>HPG Visualization</h1>
                        <iframe src="/static/hpg_visualization.html" width="100%" height="800px"></iframe>
                        <br>
                        <a href="/">Back to Home</a>
                    </body>
                </html>
            """)
        
        @self.app.get("/visualize/cfg/{node_id}")
        async def visualize_cfg(node_id: str):
            cfg = self.navigator.cfgs.get(node_id)
            if not cfg:
                raise HTTPException(status_code=404, detail=f"CFG not found for node: {node_id}")
            
            # Create a suggested output path (visualization routine will sanitize and save under static/)
            suggested_output = os.path.join(self.static_dir, self._safe_filename(node_id, prefix="cfg_"))
            file_basename = self._visualize_graph(cfg, suggested_output, f"CFG for {node_id}")
            return HTMLResponse(content=f"""
                <html>
                    <body>
                        <h1>CFG Visualization for {node_id}</h1>
                        <iframe src="/static/{file_basename}" width="100%" height="600px"></iframe>
                        <br>
                        <a href="/">Back to Home</a>
                    </body>
                 </html>
             """)
        
        @self.app.get("/visualize/pdg/{node_id}")
        async def visualize_pdg(node_id: str):
            pdg = self.navigator.pdgs.get(node_id)
            if not pdg:
                raise HTTPException(status_code=404, detail=f"PDG not found for node: {node_id}")
            
            suggested_output = os.path.join(self.static_dir, self._safe_filename(node_id, prefix="pdg_"))
            file_basename = self._visualize_graph(pdg, suggested_output, f"PDG for {node_id}")
            return HTMLResponse(content=f"""
                <html>
                    <body>
                        <h1>PDG Visualization for {node_id}</h1>
                        <iframe src="/static/{file_basename}" width="100%" height="600px"></iframe>
                        <br>
                        <a href="/">Back to Home</a>
                    </body>
                </html>
            """)
    
    def _safe_filename(self, name: str, prefix: str = "", suffix: str = ".html") -> str:
        """
        Create a filesystem-safe filename for `name`.
        Replaces invalid characters and appends a short hash for uniqueness.
        """
        # Replace characters invalid on Windows and filesystem separators with underscore
        safe = re.sub(r'[<>:"/\\|?*\s]+', '_', name)
        # Trim long names
        if len(safe) > 120:
            safe = safe[:120]
        short_hash = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
        return f"{prefix}{safe}_{short_hash}{suffix}"
    
    def _visualize_graph(self, graph, output_path: str, title: str):
        """Visualize any graph using pyvis. Returns the basename of the generated file in the static dir."""
        try:
            from pyvis.network import Network
            # Ensure the static directory exists
            os.makedirs(self.static_dir, exist_ok=True)
            
            # Determine a safe basename to use for the saved file (ignore any unsafe parts of output_path)
            base_name = os.path.splitext(os.path.basename(output_path))[0]
            safe_basename = self._safe_filename(base_name, prefix="", suffix=".html")
            final_path = os.path.join(self.static_dir, safe_basename)
            
            net = Network(height="600px", width="100%", directed=True)
            
            for node, attrs in graph.nodes(data=True):
                label = attrs.get('name', attrs.get('variable', node))
                net.add_node(node, 
                           label=label,
                           title=json.dumps(attrs, indent=2),
                           group=attrs.get('type', 'default'))
            
            for source, target, attrs in graph.edges(data=True):
                net.add_edge(source, target, title=attrs.get('type', ''))
            
            # Save to the sanitized final path
            net.save_graph(final_path)
            return safe_basename
            
        except ImportError:
            print("Pyvis not installed. Install with: pip install pyvis")
            return ""
        except OSError as e:
            # As a last resort try saving to a hashed filename inside static dir
            try:
                fallback_basename = self._safe_filename(str(time.time()), prefix="graph_", suffix=".html")
                fallback_path = os.path.join(self.static_dir, fallback_basename)
                net.save_graph(fallback_path)
                print(f"Saved graph to fallback path: {fallback_path}")
                return fallback_basename
            except Exception as ex:
                print(f"Failed to save graph (fallback too): {ex}")
                return ""
    
    def start_server(self, open_browser: bool = True):
        """Start the web server"""
        def run_server():
            uvicorn.run(self.app, host=self.host, port=self.port, log_level="info")
        
        # Start server in a separate thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        if open_browser:
            webbrowser.open(f"http://{self.host}:{self.port}")
        
        print(f"Server started at http://{self.host}:{self.port}")
        return server_thread