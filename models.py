# models.py
from typing import Dict, List, Set, Optional, Any
from pydantic import BaseModel
from enum import Enum
import networkx as nx

class NodeType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    CALL = "call"

class ASTNode(BaseModel):
    id: str
    type: NodeType
    name: str
    file_path: str
    line_start: int
    line_end: int
    children: List['ASTNode'] = []
    attributes: Dict[str, Any] = {}

class ControlFlowNode(BaseModel):
    id: str
    type: str  # 'entry', 'exit', 'statement', 'condition', 'loop'
    ast_node_id: str
    line_number: int
    code_snippet: str

class ControlFlowEdge(BaseModel):
    source: str
    target: str
    type: str  # 'normal', 'true', 'false', 'loop'

class ProgramDependencyNode(BaseModel):
    id: str
    variable: str
    line_number: int
    scope: str

class RepositoryStructure(BaseModel):
    files: List[str]
    dependencies: Dict[str, List[str]]