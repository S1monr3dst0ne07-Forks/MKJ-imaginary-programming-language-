
import sys
from dataclasses import dataclass






def lex(src):
    def kind(char):
        match char:
            case '\0': return 'terminator'
            case ' ': return 'space'
            case x if x.isalpha(): return 'iden'
            case '_': return 'iden'
            case x if x.isdigit(): return 'num'
            case '"': return 'quote'
            case '\n': return 'eos'
            case '(': return 'open'
            case ')': return 'close'
            case _: return 'sym'

    state = kind(src[0])
    ts = []
    buffer = ''

    comment = False
    string = False
    line_index = 0
    for char in src + '\0':
        this = kind(char)

        if buffer == '--': 
            #remove line indentation
            while ts[-1].strip(' ') == '':
                ts.pop(-1)
                line_index -= 1

            if line_index > 0:
                ts.append('\n')

            buffer = ''
            comment = True


        if buffer == 'Output':
            break

        if this != state and not comment and not string:
            #truncate eos
            if state == 'eos': buffer = '\n'

            if state != 'space' or line_index == 0:
                ts.append(buffer)
            line_index += 1
            buffer = ''

        if char == '"':
            string = not string
        if state == 'eos': 
            comment = False
            line_index = 0

        if not comment:
            buffer += char
        state = this

    class streamer:
        def __init__(self, ts):
            self.ts = ts

        def has(self):
            return len(self.ts) > 0

        def peek(self):
            return self.ts[0]

        def pop(self):
            return self.ts.pop(0)

        def expect(self, should):
            be = self.pop()
            if should != be:
                print(f"Lex error: Expected '{should}', but got '{be}'.")
                sys.exit(1)

    return streamer(ts)



builtin = {
    'number_nodec': 'number_nodec',
    'bool': 'bool',
    'true': True,
    'false': False,
}

@dataclass
class leaf:
    name : str

    @classmethod
    def parse(cls, s):
        return cls(s.pop())

    def run(self, env):
        if self.name.isdigit(): return int(self.name)
        if self.name[0] == '"': return self.name.strip('"')
        if self.name in builtin: return builtin[self.name]
        
        return env[self.name]["value"]




@dataclass
class expr:
    left  : "expr | leaf"
    right : "expr | leaf"
    op : str

    def run(self, env):
        l = self.left.run(env)
        r = self.right.run(env)

        return {
            '+':    l + r,
            '-':    l - r,
            '*':    l * r,
            '/':    l / r,
            '>=':   l >= r,
            '<=':   l <= r,
            '==':   l == r,
            '!=':   l != r,
            'and':  l and r,
            'or':   l or r,
        }[self.op]


    @classmethod
    def parse(cls, s):
        left = leaf.parse(s)

        if s.peek() not in ('+', '-', '*', '/', '>=', '<=', '==', '!=', 'and', 'or'):
            return left

        op = s.pop()
        right = expr.parse(s)
        return cls(left, right, op)




@dataclass
class ast_var_new:
    name : str

    @classmethod
    def parse(cls, s):
        return cls(s.pop())

    def run(self, env):
        env[self.name] = {}

@dataclass
class ast_var_set:
    name : str
    field : str
    value : expr

    def run(self, env):
        if self.name not in env:
            print(f"Error: Variable {self.name} not defined")
            sys.exit(1)

        env[self.name][self.field] = self.value.run(env)


    @classmethod
    def parse(cls, s):
        name = s.pop()
        s.expect('.')
        field = s.pop()
        s.expect('=')
        value = expr.parse(s)
        return cls(name, field, value)


@dataclass
class ast_if:
    cond : expr
    then :      "prog"
    otherwise : "prog | None" #fuck you python

    def run(self, env):
        choice = self.cond.run(env)
        if choice:
            self.then.run(env)
        else:
            self.otherwise.run(env)

    @classmethod
    def parse(cls, s, scope):
        cond = expr.parse(s)
        s.expect(':')
        s.expect('\n')
        then = ast_prog.parse(s, scope)

        if s.peek() == 'else':
            s.expect('else')
            s.expect(':')
            s.expect('\n')
            otherwise = ast_prog.parse(s, scope)
        else:
            otherwise = None

        return cls(cond, then, otherwise)


@dataclass
class ast_log:
    val : expr

    def run(self, env):
        print(self.val.run(env))

    @classmethod
    def parse(cls, s):
        s.expect('.')
        s.expect('print')
        s.expect('.')
        s.expect('(')
        val = expr.parse(s)
        s.expect(')')

        return cls(val)

@dataclass
class ast_try:
    body : "ast_prog"
    target : str
    catch : "ast_prog"

    @classmethod
    def parse(cls, s, scope):
        s.expect(':')
        s.expect('\n')
        body = ast_prog.parse(s, scope)

        s.expect('catch')
        target = s.pop()
        s.expect(':')
        s.expect('\n')
        otherwise = ast_prog.parse(s, scope)

        return cls(body, target, catch)




@dataclass
class ast_prog:
    prog : "list[ass]"

    def run(self, env):
        for stat in self.prog:
            stat.run(env)

    @classmethod 
    def parse(cls, stream, scope=0):
        stats = [] 
        while stream.has():
            #check scope
            indent = 0
            if all(x == ' ' for x in stream.peek()):
                indent = len(stream.pop()) // 4

            if indent != scope:
                break

            match stream.pop():
                case 'var':
                    if stream.peek() == '.':
                        stream.expect('.')
                        stream.expect('new')
                        stats.append(ast_var_new.parse(stream))
                    else:
                        stats.append(ast_var_set.parse(stream))
                case 'importpkg':
                    stream.expect('mkjExecutable')
                case 'mkjExecutable':
                    stream.expect(':')
                    stream.expect('activate')
                    stream.expect('(')
                    stream.expect('"main.mkj"')
                    stream.expect(')')
                case 'if':
                    stats.append(ast_if.parse(stream, scope+1))
                    continue
                case 'log':
                    stats.append(ast_log.parse(stream))
                case 'attempt':
                    stats.append(ast_try.parse(stream, scope+1))

            stream.expect('\n')

        return cls(stats) 




def main():
    path = sys.argv[1]

    with open(path, 'r') as f:
        src = f.read()

    stream = lex(src)
    root = ast_prog.parse(stream)
    root.run(env={})



if __name__ == '__main__':
    main()
