# ast_parser.py
import tree_sitter
from tree_sitter import Language, Parser
from typing import List, Dict, Optional
from models import ASTNode, NodeType
import os

class ASTParser:
    def __init__(self):
        self.parser = Parser()
        self._setup_parsers()
    
    def _setup_parsers(self):
        """Setup tree-sitter parsers for different languages"""
        try:
            # For prototype, we'll focus on Python
            Language.build_library(
                'build/tree-sitter-languages.so',
                ['vendor/tree-sitter-python']
            )
            
            PYTHON_LANGUAGE = Language('build/tree-sitter-languages.so', 'python')
            self.parser.set_language(PYTHON_LANGUAGE)
            self.languages = {'python': PYTHON_LANGUAGE}
            
        except Exception as e:
            print(f"Warning: Could not setup tree-sitter: {e}")
            self.languages = {}
    
    def parse_file(self, file_path: str, content: str) -> Optional[ASTNode]:
        """Parse file content and generate AST"""
        if not content:
            return None
            
        file_extension = os.path.splitext(file_path)[1]
        
        if file_extension == '.py' and 'python' in self.languages:
            return self._parse_python_file(content, file_path)
        else:
            # Fallback: simple line-based parsing
            return self._simple_parse_file(content, file_path)
    
    def _parse_python_file(self, content: str, file_path: str) -> ASTNode:
        """Parse Python file using tree-sitter"""
        tree = self.parser.parse(bytes(content, 'utf-8'))
        root_node = tree.root_node
        
        file_ast = ASTNode(
            id=f"file_{file_path.replace('/', '_')}",
            type=NodeType.CLASS,  # Using CLASS as file container
            name=os.path.basename(file_path),
            file_path=file_path,
            line_start=1,
            line_end=len(content.splitlines()),
            children=[]
        )
        
        # Extract functions and classes
        self._extract_python_entities(root_node, content, file_path, file_ast)
        
        return file_ast
    
    def _extract_python_entities(self, node, content: str, file_path: str, parent: ASTNode):
        """Extract functions and classes from Python AST"""
        if node.type == 'function_definition':
            func_name = None
            for child in node.children:
                if child.type == 'identifier':
                    func_name = content[child.start_byte:child.end_byte]
                    break
            
            if func_name:
                func_node = ASTNode(
                    id=f"func_{file_path.replace('/', '_')}_{func_name}",
                    type=NodeType.FUNCTION,
                    name=func_name,
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    children=[]
                )
                parent.children.append(func_node)
        
        elif node.type == 'class_definition':
            class_name = None
            for child in node.children:
                if child.type == 'identifier':
                    class_name = content[child.start_byte:child.end_byte]
                    break
            
            if class_name:
                class_node = ASTNode(
                    id=f"class_{file_path.replace('/', '_')}_{class_name}",
                    type=NodeType.CLASS,
                    name=class_name,
                    file_path=file_path,
                    line_start=node.start_point[0] + 1,
                    line_end=node.end_point[0] + 1,
                    children=[]
                )
                parent.children.append(class_node)
                
                # Recursively extract methods
                for child in node.children:
                    if child.type == 'block':
                        for block_child in child.children:
                            self._extract_python_entities(block_child, content, file_path, class_node)
        
        # Recursively process children
        for child in node.children:
            self._extract_python_entities(child, content, file_path, parent)
    
    def _simple_parse_file(self, content: str, file_path: str) -> ASTNode:
        """Simple fallback parser for non-Python files"""
        lines = content.splitlines()
        
        file_ast = ASTNode(
            id=f"file_{file_path.replace('/', '_')}",
            type=NodeType.CLASS,
            name=os.path.basename(file_path),
            file_path=file_path,
            line_start=1,
            line_end=len(lines),
            children=[]
        )
        
        # Simple pattern matching for functions/classes
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('def ') and line.endswith(':'):
                func_name = line[4:-1].split('(')[0]
                func_node = ASTNode(
                    id=f"func_{file_path.replace('/', '_')}_{func_name}_{i}",
                    type=NodeType.FUNCTION,
                    name=func_name,
                    file_path=file_path,
                    line_start=i + 1,
                    line_end=min(i + 10, len(lines)),  # Estimate
                    children=[]
                )
                file_ast.children.append(func_node)
            
            elif line.startswith('class ') and line.endswith(':'):
                class_name = line[6:-1].split('(')[0].split(':')[0]
                class_node = ASTNode(
                    id=f"class_{file_path.replace('/', '_')}_{class_name}_{i}",
                    type=NodeType.CLASS,
                    name=class_name,
                    file_path=file_path,
                    line_start=i + 1,
                    line_end=min(i + 20, len(lines)),  # Estimate
                    children=[]
                )
                file_ast.children.append(class_node)
        
        return file_ast