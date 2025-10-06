# web_server.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
import uvicorn
import json
import os
from typing import Dict, Any
import webbrowser
import threading
import time

class GraphVisualizationServer:
    def __init__(self, navigator_module, host: str = "localhost", port: int = 8000):
        self.navigator = navigator_module
        self.host = host
        self.port = port
        self.app = FastAPI(title="CodeIQ Navigator", 
                          description="Graph Visualization API")
        
        # Create static directory for visualizations
        self.static_dir = "static"
        os.makedirs(self.static_dir, exist_ok=True)
        self.app.mount("/static", StaticFiles(directory=self.static_dir), name="static")
        
        self.templates = Jinja2Templates(directory="templates")
        self._setup_routes()
    
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
                raise HTTPException(status_code=404, detail="No CFGs built yet")
            
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
                raise HTTPException(status_code=404, detail="No PDGs built yet")
            
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
        
        @self.app.get("/visualize/hpg")
        async def visualize_hpg():
            if not self.navigator.hpg:
                raise HTTPException(status_code=404, detail="HPG not built yet")
            
            output_path = os.path.join(self.static_dir, "hpg_visualization.html")
            self.navigator.visualize_hpg(output_path)
            # Ensure any pyvis assets are moved into our static folder and paths fixed
            try:
                self._postprocess_pyvis_html(output_path)
            except Exception:
                pass
            
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

            # Sanitize node_id for use in a filename so we don't create invalid paths
            safe_name = self._sanitize_filename(node_id)
            output_filename = f"cfg_{safe_name}.html"
            output_path = os.path.join(self.static_dir, output_filename)
            self._visualize_graph(cfg, output_path, f"CFG for {node_id}")

            return HTMLResponse(content=f"""
                <html>
                    <body>
                        <h1>CFG Visualization for {node_id}</h1>
                        <iframe src="/static/{output_filename}" width="100%" height="600px"></iframe>
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

            safe_name = self._sanitize_filename(node_id)
            output_filename = f"pdg_{safe_name}.html"
            output_path = os.path.join(self.static_dir, output_filename)
            self._visualize_graph(pdg, output_path, f"PDG for {node_id}")

            return HTMLResponse(content=f"""
                <html>
                    <body>
                        <h1>PDG Visualization for {node_id}</h1>
                        <iframe src="/static/{output_filename}" width="100%" height="600px"></iframe>
                        <br>
                        <a href="/">Back to Home</a>
                    </body>
                </html>
            """)
        
        @self.app.get("/api/files")
        async def get_files():
            files = list(self.navigator.ast_cache.keys())
            return JSONResponse(content={"files": files})
    
    def _visualize_graph(self, graph, output_path: str, title: str):
        """Visualize any graph using pyvis"""
        try:
            from pyvis.network import Network
            
            net = Network(height="600px", width="100%", directed=True)
            
            for node, attrs in graph.nodes(data=True):
                label = attrs.get('name', attrs.get('variable', node))
                net.add_node(node, 
                           label=label,
                           title=json.dumps(attrs, indent=2),
                           group=attrs.get('type', 'default'))
            
            for source, target, attrs in graph.edges(data=True):
                net.add_edge(source, target, title=attrs.get('type', ''))
            
            net.save_graph(output_path)
            # Post-process generated HTML to move any pyvis assets and fix references
            try:
                self._postprocess_pyvis_html(output_path)
            except Exception:
                pass
            
        except ImportError:
            print("Pyvis not installed. Install with: pip install pyvis")

    def _sanitize_filename(self, name: str) -> str:
        """Return a filesystem-safe filename fragment for a given name."""
        # Replace path separators and other URL-unsafe characters
        import re
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)
        # Truncate to a reasonable length
        return safe[:200]

    def _postprocess_pyvis_html(self, output_path: str):
        """Move pyvis-generated lib assets into static/lib and fix HTML references to /static/lib/"""
        html_dir = os.path.dirname(output_path) or "."
        generated_lib_dir = os.path.join(html_dir, "lib")
        target_lib_dir = os.path.join(self.static_dir, "lib")

        if os.path.isdir(generated_lib_dir):
            import shutil
            os.makedirs(target_lib_dir, exist_ok=True)
            for fname in os.listdir(generated_lib_dir):
                src = os.path.join(generated_lib_dir, fname)
                dst = os.path.join(target_lib_dir, fname)
                try:
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.move(src, dst)
                    else:
                        if os.path.exists(dst):
                            os.remove(dst)
                        shutil.move(src, dst)
                except Exception:
                    # non-fatal
                    pass

        # Rewrite the generated HTML to point to /static/lib/ instead of lib/
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                html = f.read()

            updated_html = html.replace('src="lib/', 'src="/static/lib/').replace('href="lib/', 'href="/static/lib/')

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(updated_html)
        except Exception:
            pass
    
    def start_server(self, open_browser: bool = True):
        """Start the web server"""
        def run_server():
            uvicorn.run(self.app, host=self.host, port=self.port)
        
        # Start server in a separate thread
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        if open_browser:
            webbrowser.open(f"http://{self.host}:{self.port}")
        
        print(f"Server started at http://{self.host}:{self.port}")
        return server_thread