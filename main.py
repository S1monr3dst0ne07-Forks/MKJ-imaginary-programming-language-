
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
                print(f"Lex error: Should {should}, is {be}.")
                sys.exit(1)

    return streamer(ts)



@dataclass
class leaf:
    name : str

    @classmethod
    def parse(cls, s):
        return cls(s.pop())


@dataclass
class expr:
    left  : "expr | leaf"
    right : "expr | leaf"
    op : str

    @classmethod
    def parse(cls, s):
        left = leaf.parse(s)

        if s.peek() not in ('>=', '<=', '==', '!=', 'and', 'or'):
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

@dataclass
class ast_var_set:
    name : str
    field : str
    value : expr

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
    then : "list[stat]"
    otherwise : "list[stat] | None" #fuck you python

    @classmethod
    def parse(cls, s):
        cond = expr.parse(s)
        s.expect(':')
        s.expect('\n')
        scope = 1 #hard coded
        then = parse(s, scope)

        if s.peek() == 'else':
            s.expect('else')
            s.expect(':')
            s.expect('\n')
            otherwise = parse(s, scope)
        else:
            otherwise = None

        return cls(cond, then, otherwise)


@dataclass
class ast_log:
    val : expr

    @classmethod
    def parse(cls, s):
        s.expect('.')
        s.expect('print')
        s.expect('.')
        s.expect('(')
        val = expr.parse(s)
        s.expect(')')

        return cls(val)



def parse(stream, scope=0):
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
                stats.append(ast_if.parse(stream))
                continue
            case 'log':
                stats.append(ast_log.parse(stream))

        assert stream.pop() == '\n' #newline

    return stats 






def main():
    path = sys.argv[1]

    with open(path, 'r') as f:
        src = f.read()

    stream = lex(src)
    root = parse(stream)

    print(root)


if __name__ == '__main__':
    main()
