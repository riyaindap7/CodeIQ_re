# graph_builders.py
import networkx as nx
from typing import Dict, List, Set, Optional
from models import ASTNode, ControlFlowNode, ControlFlowEdge, ProgramDependencyNode
from collections import defaultdict

class HPGBuilder:
    """Hierarchical Program Graph Builder"""
    
    def build(self, ast_nodes: List[ASTNode]) -> nx.DiGraph:
        graph = nx.DiGraph()
        
        for ast_node in ast_nodes:
            self._add_ast_node_to_graph(ast_node, graph, None)
        
        return graph
    
    def _add_ast_node_to_graph(self, ast_node: ASTNode, graph: nx.DiGraph, parent_id: Optional[str]):
        graph.add_node(ast_node.id, 
                      type=ast_node.type.value,
                      name=ast_node.name,
                      file_path=ast_node.file_path,
                      line_start=ast_node.line_start,
                      line_end=ast_node.line_end)
        
        if parent_id:
            graph.add_edge(parent_id, ast_node.id, type="contains")
        
        for child in ast_node.children:
            self._add_ast_node_to_graph(child, graph, ast_node.id)

class CFGBuilder:
    """Control Flow Graph Builder"""
    
    def build(self, ast_node: ASTNode, content: str) -> nx.DiGraph:
        graph = nx.DiGraph()
        lines = content.splitlines()
        
        # Simple CFG construction based on AST structure
        entry_node = ControlFlowNode(
            id=f"entry_{ast_node.id}",
            type="entry",
            ast_node_id=ast_node.id,
            line_number=ast_node.line_start,
            code_snippet=lines[ast_node.line_start-1] if ast_node.line_start <= len(lines) else ""
        )
        
        exit_node = ControlFlowNode(
            id=f"exit_{ast_node.id}",
            type="exit", 
            ast_node_id=ast_node.id,
            line_number=ast_node.line_end,
            code_snippet=lines[ast_node.line_end-1] if ast_node.line_end <= len(lines) else ""
        )
        
        graph.add_node(entry_node.id, **entry_node.dict())
        graph.add_node(exit_node.id, **exit_node.dict())
        
        # Add basic flow from entry to exit
        graph.add_edge(entry_node.id, exit_node.id, type="normal")
        
        return graph

class PDGBuilder:
    """Program Dependency Graph Builder"""
    
    def build(self, ast_node: ASTNode, content: str) -> nx.DiGraph:
        graph = nx.DiGraph()
        lines = content.splitlines()
        
        # Simple data dependency analysis
        variables = self._extract_variables(content, ast_node.line_start, ast_node.line_end)
        
        for i, (var, line_num) in enumerate(variables):
            node = ProgramDependencyNode(
                id=f"var_{ast_node.id}_{i}",
                variable=var,
                line_number=line_num,
                scope=ast_node.name
            )
            graph.add_node(node.id, **node.dict())
        
        # Add basic dependencies (simplified)
        for i in range(len(variables) - 1):
            graph.add_edge(f"var_{ast_node.id}_{i}", f"var_{ast_node.id}_{i+1}", type="data_flow")
        
        return graph
    
    def _extract_variables(self, content: str, start_line: int, end_line: int) -> List[tuple]:
        """Extract variable assignments (simplified)"""
        lines = content.splitlines()
        variables = []
        
        for i in range(start_line - 1, min(end_line, len(lines))):
            line = lines[i].strip()
            if '=' in line and not line.startswith('#'):
                var_name = line.split('=')[0].strip()
                if var_name and not var_name.startswith(' '):
                    variables.append((var_name, i + 1))
        
        return variables