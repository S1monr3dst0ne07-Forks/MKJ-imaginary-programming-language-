
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

        def push(self, x):
            self.ts.insert(0, x)

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
    'number_fixed': 'number_fixed',
    'string': 'string',
    'bool': 'bool',
    'true': True,
    'false': False,
}

@dataclass
class leaf:
    name : str
    method : "str | None"
    args : "list[a]"

    @classmethod
    def parse(cls, s):
        name = s.pop()
        method = None
        args = []

        if s.peek() == '.':
            s.expect('.')
            method = s.pop()

            match method:
                case 'length' | 'upper' | 'lower': pass
                case 'find': args.append(s.pop().strip('"'))

        return cls(name, method, args)

    def run(self, env, fixed=False):
        if self.method is not None:
            val = env[self.name]["value"]
            match self.method:
                case 'length': return len(val)
                case 'upper':  return val.upper()
                case 'lower':  return val.lower()
                case 'find':   return self.args[0] if self.args[0] in val else 'null'

        if self.name.isdigit(): return int(self.name)
        if self.name[0] == '"': return self.name.strip('"')
        if self.name in builtin: return builtin[self.name]
        
        if "value" in env[self.name]:
            return env[self.name]["value"]

        return env[self.name]




@dataclass
class expr:
    left  : "expr | leaf"
    right : "expr | leaf"
    op : str

    def run(self, env, fixed=False):
        l = self.left.run(env)
        r = self.right.run(env)

        return {
            '+':    lambda l,r: l + r,
            '-':    lambda l,r: l - r,
            '*':    lambda l,r: l * r,
            '/':    lambda l,r: 0 if r == 0 and fixed else l / r,
            '>=':   lambda l,r: l >= r,
            '<=':   lambda l,r: l <= r,
            '==':   lambda l,r: l == r,
            '!=':   lambda l,r: l != r,
            'and':  lambda l,r: l and r,
            'or':   lambda l,r: l or r,
            '..':   lambda l,r: str(l) + str(r),
        }[self.op](l,r)


    @classmethod
    def parse(cls, s):
        left = leaf.parse(s)

        if s.peek() not in ('+', '-', '*', '/', '>=', '<=', '==', '!=', 'and', 'or', '..'):
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

        fixed = "type" in env[self.name] and env[self.name]["type"] == 'number_fixed'
        env[self.name][self.field] = self.value.run(env, fixed)


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
        out = self.val.run(env)
        if type(out) is dict:
            for k, v in out.items():
                print(f"{k}: {v}")
        else:
            print(out)

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

    def run(self, env):
        try:
            self.body.run(env)
        except Exception as E:
            env[self.target] = {}
            env[self.target]["value"] = str(E)
            self.catch.run(env)

    @classmethod
    def parse(cls, s, scope):
        s.expect(':')
        s.expect('\n')
        body = ast_prog.parse(s, scope)

        s.expect('catch')
        target = s.pop()
        s.expect(':')
        s.expect('\n')
        catch = ast_prog.parse(s, scope)

        return cls(body, target, catch)


@dataclass
class ast_class:
    name : str

    def run(self, env):
        env[self.name] = {}

    @classmethod
    def parse(cls, s):
        return cls(s.pop())

@dataclass
class ast_func:
    name : str
    params : "list[]"
    body : "prog"

    def run(self, env):
        env["_fn"][self.name] = self

    def call(self, env, args, constructer=None):
        for name, value in zip(self.params, args):
            env[name] = value

        env["_con"] = constructer
        self.body.run(env)

    @classmethod
    def parse(cls, s, scope):
        name = s.pop()
        params = []
        s.expect('(')
        while s.peek() != ')':
            params.append(s.pop())
            if s.peek() == ',': s.pop()
        s.expect(')')
        s.expect(':')
        s.expect('\n')
        body = ast_prog.parse(s, scope)
        s.push('\n')
        return cls(name, params, body)

@dataclass
class ast_self:
    fields : list[str]

    def run(self, env):
        for name in self.fields:
            env[env["_con"]][name] = env[name]

    @classmethod
    def parse(cls, s):
        fields = []
        while s.peek() != '\n':
            fields.append(s.pop())
            if s.peek() == ',': s.pop()
        return cls(fields)

@dataclass
class ast_call:
    fn_name : str
    constructer : "str | None"
    params : list[expr]

    def run(self, env):
        param_vals = [x.run(env) for x in self.params]
        env["_fn"][self.fn_name].call(env, param_vals, self.constructer)

    @classmethod
    def parse(cls, s, constructer=None):
        fn_name = s.pop()
        params = []
        s.expect('(')
        while s.peek() != ')':
            params.append(expr.parse(s))
            if s.peek() == ',': s.pop()
        s.expect(')')
        return cls(fn_name, constructer, params)






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

            stat = None
            match stream.pop():
                case 'var':
                    if stream.peek() == '.':
                        stream.expect('.')
                        stream.expect('new')
                        stat = ast_var_new.parse(stream)
                    else:
                        stat = ast_var_set.parse(stream)
                case 'importpkg':
                    stream.expect('mkjExecutable')
                case 'mkjExecutable':
                    stream.expect(':')
                    stream.expect('activate')
                    stream.expect('(')
                    stream.expect('"main.mkj"')
                    stream.expect(')')
                case 'if':
                    stat = ast_if.parse(stream, scope+1)
                    continue
                case 'log':
                    stat = ast_log.parse(stream)
                case 'attempt':
                    stat = ast_try.parse(stream, scope+1)
                case 'class':
                    stream.expect('.')
                    stream.expect('new')
                    stat = ast_class.parse(stream)
                case 'function':
                    stat = ast_func.parse(stream, scope+1)
                case 'para':
                    stream.pop()
                    stream.expect('.')
                    stream.pop()
                    stream.expect('=')
                    stream.pop()
                case 'self':
                    stat = ast_self.parse(stream)

                case x if stream.peek() == '.':
                    stream.expect('.')
                    stream.expect('new')
                    stat = ast_call.parse(stream, constructer=x)
                
                case x:
                    stream.push(x)
                    stat = ast_call.parse(stream)

            if stat is not None:
                stats.append(stat)


            if stream.has():
                stream.expect('\n')

        return cls(stats) 




def main():
    path = sys.argv[1]

    with open(path, 'r') as f:
        src = f.read()

    stream = lex(src)
    root = ast_prog.parse(stream)
    root.run(env={
        "_fn" : {}, #functions
    })



if __name__ == '__main__':
    main()
