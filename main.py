
import sys






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

    #print("".join(ts))
    print(ts)








def main():
    path = sys.argv[1]

    with open(path, 'r') as f:
        src = f.read()

    lex(src)


if __name__ == '__main__':
    main()
