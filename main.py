# main_app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
from step5_navigator import NavigatorModule
from web_server import GraphVisualizationServer
import uvicorn
import webbrowser
import threading

class RepositoryRequest(BaseModel):
    repo_url: str

class CodeIQApplication:
    def __init__(self):
        self.navigator = NavigatorModule(max_workers=4)
        self.app = FastAPI(title="CodeIQ Navigator API")
        self.server = GraphVisualizationServer(self.navigator)
        self._setup_routes()
    
    def _setup_routes(self):
        # Include all routes from the visualization server
        for route in self.server.app.routes:
            self.app.routes.append(route)
        
        # Add analysis endpoint
        @self.app.post("/api/analyze")
        async def analyze_repository(request: RepositoryRequest):
            try:
                result = await self.navigator.analyze_repository(request.repo_url)
                return result
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        
        @self.app.get("/api/status")
        async def get_status():
            return {
                "status": "ready",
                "has_analysis": self.navigator.hpg is not None,
                "files_analyzed": len(self.navigator.ast_cache)
            }

def main():
    # Create and setup application
    codeiq_app = CodeIQApplication()
    
    # Start the server
    print("Starting CodeIQ Navigator Server...")
    print("Access the web interface at: http://localhost:8000")
    
    # Open browser automatically
    webbrowser.open("http://localhost:8000")
    
    # Run the server
    uvicorn.run(codeiq_app.app, host="localhost", port=8000, log_level="info")

if __name__ == "__main__":
    main()