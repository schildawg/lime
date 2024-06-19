from llvmlite import ir

from AST import Node, NodeType, Program, Expression, Statement
from AST import ExpressionStatement, LetStatement, BlockStatement, FunctionStatement, ReturnStatement, AssignStatement, IfStatement
from AST import InfixExpression, CallExpression
from AST import IntegerLiteral, FloatLiteral, IdentifierLiteral, BooleanLiteral

from Environment import Environment

class Compiler:
    def __init__(self) -> None:
        self.type_map: dict[str, ir.Type] = {
            'int': ir.IntType(32),
            'float': ir.FloatType(),
            'bool': ir.IntType(1)
        }

        self.module: ir.Module = ir.Module('main')
        self.builder: ir.IRBuilder = ir.IRBuilder()
        self.env : Environment = Environment()

        self.errors: list[str] = []

        self.__initialize_builtins()


    def __initialize_builtins(self) -> None:
        def __init_booleans() -> tuple[ir.GlobalVariable, ir.GlobalVariable]:
            bool_type: ir.Type = self.type_map['bool']

            true_var = ir.GlobalVariable(self.module, bool_type, 'true')
            true_var.initializer = ir.Constant(bool_type, 1)
            true_var.global_constant = True

            false_var = ir.GlobalVariable(self.module, bool_type, 'false')
            false_var.initializer = ir.Constant(bool_type, 0)
            false_var.global_constant = True

            return true_var, false_var
        
        true_var, false_var = __init_booleans()
        self.env.define('true', true_var, true_var.type)
        self.env.define('false', false_var, false_var.type)

    def compile(self, node: Node) -> None:
        match node.type():
            case NodeType.Program:
                self.__visit_program(node)

            # Statements
            case NodeType.ExpressionStatement:
                self.__visit_expression_statement(node)
            case NodeType.LetStatement:
                self.__visit_let_statement(node)
            case NodeType.FunctionStatement:
                self.__visit_function_statement(node)
            case NodeType.BlockStatement:
                self.__visit_block_statement(node)
            case NodeType.ReturnStatement:
                self.__visit_return_statement(node)
            case NodeType.AssignStatement:
                self.__visit_assign_statement(node)
            case NodeType.IfStatement:
                self.__visit_if_statement(node)

            case NodeType.InfixExpression:
                self.__visit_infix_expression(node)
            case NodeType.CallExpression:
                self.__visit_call_expression(node)
            
    # region Visit Methods
    def __visit_program(self, node: Program) -> None:
        for stmt in node.statements:
            self.compile(stmt)


    # region Statements
    def __visit_expression_statement(self, node: ExpressionStatement) -> None:
        self.compile(node.expr)  

    def __visit_let_statement(self, node: LetStatement) -> None:
        name: str = node.name.value
        value: Expression = node.value
        value_type: str = node.value_type

        value, Type = self.__resolve_value(node=value)
        
        if self.env.lookup(name) is None:
            # Define and allocate the value
            ptr = self.builder.alloca(Type)

            # Storing the value to the ptr
            self.builder.store(value, ptr)

            # Add the variable to the environment
            self.env.define(name, ptr, Type)
        else:
            ptr, _ = self.env.lookup(name)
            self.builder.store(value, ptr)
    
    def __visit_block_statement(self, node: BlockStatement) -> None:
        for stmt in node.statements:
            self.compile(stmt)
    
    def __visit_return_statement(self, node: ReturnStatement) -> None:
        value: Expression = node.return_value
        value, Type = self.__resolve_value(value)

        self.builder.ret(value)
    
    def __visit_function_statement(self, node: FunctionStatement) -> None:
        name: str = node.name.value
        body: BlockStatement = node.body
        params: list[IdentifierLiteral] = node.parameters

        param_names: list[str] = [p.value for p in params]

        # Keep track of the types for each parameter
        param_types: list[ir.Type] = [] # TODO

        return_type: ir.Type = self.type_map[node.return_type]

        fnty: ir.FunctionType = ir.FunctionType(return_type, param_types)
        func: ir.Fuction = ir.Function(self.module, fnty, name=name)

        block: ir.Block = func.append_basic_block(f"{name}_entry")

        previous_builder = self.builder
        
        self.builder = ir.IRBuilder(block)

        previous_env = self.env

        self.env = Environment(parent=self.env)
        self.env.define(name, func, return_type)

        self.compile(body)

        self.env = previous_env
        self.env.define(name, func, return_type)

        self.builder = previous_builder

    def __visit_assign_statement(self, node: AssignStatement) -> None:
        name: str = node.ident.value
        value: Expression = node.right_value

        value, Type = self.__resolve_value(value)
        
        if self.env.lookup(name) is None:
            self.errors.append(f"COMPILE ERROR: Identifier {name} has not been declared before it was re-assigned")
        else:
            ptr, _ = self.env.lookup(name)
            self.builder.store(value, ptr)
    
    def __visit_if_statement(self, node: IfStatement) -> None:
        condition = node.condition
        consequence = node.consequence
        alternative = node.alternative

        test, _ = self.__resolve_value(condition)

        if alternative is None:
            with self.builder.if_then(test):
                self.compile(consequence)
        else:
            with self.builder.if_else(test) as (true, otherwise):
                with true:
                    self.compile(consequence)
                with otherwise:
                    self.compile(alternative)
                
    # endregion

    # region Expressions
    def __visit_infix_expression(self, node: InfixExpression) -> None:
        operator: str = node.operator
        left_value, left_type = self.__resolve_value(node.left_node)
        right_value, right_type = self.__resolve_value(node.right_node)

        value = None
        Type = None

        if isinstance(right_type, ir.IntType) and isinstance(left_type, ir.IntType):
            Type = self.type_map['int']
            match operator:
                case '+':
                    value = self.builder.add(left_value, right_value)
                case '-':
                    value = self.builder.sub(left_value, right_value)
                case '*':
                    value = self.builder.mul(left_value, right_value)
                case '/':
                    value = self.builder.sdiv(left_value, right_value)
                case '%':
                    value = self.builder.srem(left_value, right_value)
                case '^':
                    # TODO
                    pass
                case '<':
                    value = self.builder.icmp_signed('<', left_value, right_value)
                    Type = ir.IntType(1)
                case '<=':
                    value = self.builder.icmp_signed('<=', left_value, right_value)
                    Type = ir.IntType(1)
                case '>':
                    value = self.builder.icmp_signed('>', left_value, right_value)
                    Type = ir.IntType(1)
                case '>=':
                    value = self.builder.icmp_signed('>=', left_value, right_value)
                    Type = ir.IntType(1)
                case '==':
                    value = self.builder.icmp_signed('==', left_value, right_value)
                    Type = ir.IntType(1)
                case '!=':
                    value = self.builder.icmp_signed('!=', left_value, right_value)
                    Type = ir.IntType(1)

        if isinstance(right_type, ir.FloatType) and isinstance(left_type, ir.FloatType):
            Type = self.type_map['float']
            match operator:
                case '+':
                    value = self.builder.fadd(left_value, right_value)
                case '-':
                    value = self.builder.fsub(left_value, right_value)
                case '*':
                    value = self.builder.fmul(left_value, right_value)
                case '/':
                    value = self.builder.fdiv(left_value, right_value)
                case '%':
                    value = self.builder.frem(left_value, right_value)
                case '^':
                    # TODO
                    pass
                case '<':
                    value = self.builder.fcmp_ordered('<', left_value, right_value)
                    Type = ir.IntType(1)
                case '<=':
                    value = self.builder.fcmp_ordered('<=', left_value, right_value)
                    Type = ir.IntType(1)
                case '>':
                    value = self.builder.fcmp_ordered('>', left_value, right_value)
                    Type = ir.IntType(1)
                case '>=':
                    value = self.builder.fcmp_ordered('>=', left_value, right_value)
                    Type = ir.IntType(1)
                case '==':
                    value = self.builder.fcmp_ordered('==', left_value, right_value)
                    Type = ir.IntType(1)   
                case '!=':
                    value = self.builder.fcmp_ordered('!=', left_value, right_value)
                    Type = ir.IntType(1)                
        return value, Type

    def __visit_call_expression(self, node: CallExpression) -> None:
        name: str = node.function.value
        params: list[Expression] = node.arguments

        args = []
        types = []

        match name:
            case _:
                func, ret_type = self.env.lookup(name)
                ret = self.builder.call(func, args)

        return ret, ret_type

    # endregion

    # endregion

    # region Helper Methods
    def __resolve_value(self, node: Expression, value_type: str = None) -> tuple[ir.Value, ir.Type]:
        match node.type():
            case NodeType.IntegerLiteral:
               node: IntegerLiteral = node
               value, Type = node.value, self.type_map['int' if value_type is None else value_type]
               return ir.Constant(Type, value), Type
            case NodeType.FloatLiteral:
               node: FloatLiteral = node
               value, Type = node.value, self.type_map['float' if value_type is None else value_type]
               return ir.Constant(Type, value), Type
            case NodeType.IdentifierLiteral:
               node: IdentifierLiteral = node
               ptr, Type = self.env.lookup(node.value)
               return self.builder.load(ptr), Type
            case NodeType.BooleanLiteral:
               node: BooleanLiteral = node
               return ir.Constant(ir.IntType(1), 1 if node.value else 0), ir.IntType(1)
            # Expression Values
            case NodeType.InfixExpression:
                return self.__visit_infix_expression(node)
            case NodeType.CallExpression:
                return self.__visit_call_expression(node)            

    # endregion