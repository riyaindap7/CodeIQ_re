# navigator.py
import asyncio
from typing import Dict, List, Optional
from step2_repo_parser import RepositoryParser
from step3_ast_parser import ASTParser
from step4_graph_builder import HPGBuilder, CFGBuilder, PDGBuilder
from models import ASTNode
import networkx as nx
import json
from fastapi import HTTPException

class NavigatorModule:
    def __init__(self, max_workers: int = 4):
        self.repository_parser = RepositoryParser(max_workers)
        self.ast_parser = ASTParser()
        self.hpg_builder = HPGBuilder()
        self.cfg_builder = CFGBuilder()
        self.pdg_builder = PDGBuilder()
        
        self.ast_cache: Dict[str, ASTNode] = {}
        self.hpg: Optional[nx.DiGraph] = None
        self.cfgs: Dict[str, nx.DiGraph] = {}
        self.pdgs: Dict[str, nx.DiGraph] = {}
        self.file_contents: Dict[str, str] = {}
    
    def clear_analysis(self):
        """Clear previous analysis results"""
        self.ast_cache.clear()
        self.hpg = None
        self.cfgs.clear()
        self.pdgs.clear()
        self.file_contents.clear()
        print("Cleared previous analysis results")
    
    async def analyze_repository(self, repo_url: str) -> Dict:
        """Main method to analyze a GitHub repository"""
        print(f"Starting analysis of repository: {repo_url}")
        
        # Clear previous analysis
        self.clear_analysis()
        
        # Step 1: Parse repository and get file contents
        self.file_contents = await self.repository_parser.process_repository(repo_url)
        
        if not self.file_contents:
            raise HTTPException(status_code=400, detail="No files found in repository or failed to clone")
        
        # Step 2: Build ASTs for each file
        print("Building ASTs...")
        ast_nodes = []
        for file_path, content in self.file_contents.items():
            ast_node = self.ast_parser.parse_file(file_path, content)
            if ast_node:
                self.ast_cache[file_path] = ast_node
                ast_nodes.append(ast_node)
        
        if not ast_nodes:
            raise HTTPException(status_code=400, detail="No valid code files found to analyze")
        
        # Step 3: Build Hierarchical Program Graph
        print("Building HPG...")
        self.hpg = self.hpg_builder.build(ast_nodes)
        
        # Step 4: Build Control Flow Graphs for functions
        print("Building CFGs...")
        for ast_node in ast_nodes:
            self._build_cfgs_for_node(ast_node, self.file_contents.get(ast_node.file_path, ""))
        
        # Step 5: Build Program Dependency Graphs
        print("Building PDGs...")
        for ast_node in ast_nodes:
            self._build_pdgs_for_node(ast_node, self.file_contents.get(ast_node.file_path, ""))
        
        # Generate analysis report
        report = self._generate_analysis_report()
        
        print("Analysis completed!")
        return report
    
    def _build_cfgs_for_node(self, ast_node: ASTNode, content: str):
        """Build CFGs for a node and its children"""
        if ast_node.type.value in ['function', 'method']:
            cfg = self.cfg_builder.build(ast_node, content)
            self.cfgs[ast_node.id] = cfg
        
        for child in ast_node.children:
            self._build_cfgs_for_node(child, content)
    
    def _build_pdgs_for_node(self, ast_node: ASTNode, content: str):
        """Build PDGs for a node and its children"""
        if ast_node.type.value in ['function', 'method']:
            pdg = self.pdg_builder.build(ast_node, content)
            self.pdgs[ast_node.id] = pdg
        
        for child in ast_node.children:
            self._build_pdgs_for_node(child, content)
    
    def _generate_analysis_report(self) -> Dict:
        """Generate analysis report with statistics"""
        total_functions = 0
        total_classes = 0
        
        for node in self.ast_cache.values():
            for child in node.children:
                if child.type.value == 'function':
                    total_functions += 1
                elif child.type.value == 'class':
                    total_classes += 1
        
        report = {
            "repository_analysis": {
                "total_files": len(self.ast_cache),
                "total_functions": total_functions,
                "total_classes": total_classes,
                "hpg_nodes": len(self.hpg.nodes) if self.hpg else 0,
                "hpg_edges": len(self.hpg.edges) if self.hpg else 0,
                "cfgs_built": len(self.cfgs),
                "pdgs_built": len(self.pdgs),
                "analysis_timestamp": asyncio.get_event_loop().time()
            },
            "file_breakdown": [
                {
                    "file_path": file_path,
                    "functions": [child.name for child in ast_node.children 
                                 if child.type.value == 'function'],
                    "classes": [child.name for child in ast_node.children 
                               if child.type.value == 'class']
                }
                for file_path, ast_node in self.ast_cache.items()
            ]
        }
        
        return report
    
    def get_analysis_status(self) -> Dict:
        """Get current analysis status"""
        return {
            "has_analysis": self.hpg is not None,
            "files_analyzed": len(self.ast_cache),
            "cfgs_built": len(self.cfgs),
            "pdgs_built": len(self.pdgs),
            "hpg_exists": self.hpg is not None
        }
    
    def visualize_hpg(self, output_path: str = "static/hpg_visualization.html"):
        """Generate visualization of HPG"""
        if not self.hpg:
            print("No HPG available to visualize")
            return
        
        try:
            from pyvis.network import Network
            
            net = Network(height="800px", width="100%", directed=True)
            
            for node, attrs in self.hpg.nodes(data=True):
                net.add_node(node, 
                           label=f"{attrs.get('name', '')}\n({attrs.get('type', '')})",
                           title=f"File: {attrs.get('file_path', '')}\nLines: {attrs.get('line_start', '')}-{attrs.get('line_end', '')}",
                           group=attrs.get('type', ''))
            
            for source, target, attrs in self.hpg.edges(data=True):
                net.add_edge(source, target, title=attrs.get('type', ''))
            
            net.save_graph(output_path)
            print(f"HPG visualization saved to {output_path}")
            
        except ImportError:
            print("Pyvis not installed. Install with: pip install pyvis")
    
    def save_analysis(self, output_path: str = "analysis_results.json"):
        """Save analysis results to JSON file"""
        report = self._generate_analysis_report()
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Analysis results saved to {output_path}")