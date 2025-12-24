
import sys






def lex(src):
    def kind(char):
        match char:
            case '\0': return 'terminator'
            case ' ': return 'space'
            case x if x.isalpha(): return 'iden'
            case '_': return 'iden'
            case x if x.isdigit(): return 'num'
            case '"': 'quote'
            case _: return 'sym'


    lines = []
    for line in src.split('\n'):
        words = []

        if not line.strip(): continue

        #stop at output
        if line.strip() == "Output:": break

        buffer = ''
        state = kind(line[0])
        scope_space_done = False
        string = False
        comment = False
        for char in list(line) + ['\0']:
            this = kind(char)

            if buffer == '--': comment = True
            if char == '\n': comment = False

            if state != this and not string and not comment:
                words.append(buffer)
                buffer = ''

                if state == 'space' and scope_space_done:
                    words.pop(-1)
                scope_space_done = True

            if char == '"': string = not string

            if not comment:
                buffer += char
            state = this

        # check token
        if [x for x in words if x.strip()]:
            lines.append(words)

    print(lines)
            








def main():
    path = sys.argv[1]

    with open(path, 'r') as f:
        src = f.read()

    lex(src)


if __name__ == '__main__':
    main()
