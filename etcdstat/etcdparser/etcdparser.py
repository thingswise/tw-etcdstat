class TreeParser(object):

    def __init__(self, tmpl):
        self.root = parse_tree(tmpl)

    def render(self, input_doc):
        return self.root.render(Context(input_doc, {}))

def parse_tree(tmpl):
    if isinstance(tmpl, dict):
        result = ObjectValueTemplate()
        for n, v in tmpl.iteritems():
            if len(n) > 3 and n[0] == "^" and n[1] == "(":
                i = n.find(")", 2)
                if i < 0:
                    raise ValueError("Invalid template: %s" % n)
                path = n[2:i].strip()
                name = n[i+1:].strip()
                if len(name) <= 0:
                    raise ValueError("Invalid template: %s" % n)
                result.put(NameTemplate(path_template=PathTemplate(path), name_template=StrTemplate(name)), parse_tree(v))
            else:
                result.put(NameTemplate(name_template=StrTemplate(n)), parse_tree(v))
        return result
    elif isinstance(tmpl, list):
        result = ArrayValueTemplate()
        for v in tmpl:
            result.append(parse_tree(v))
        return result
    elif isinstance(tmpl, str):
        if len(tmpl) > 3 and tmpl[0] == "^" and tmpl[1] == "(" and tmpl[-1] == ")":
            path = tmpl[2:-1].strip()
            if len(path) <= 0:
                raise ValueError("Invalid template: %s" % tmpl)
            return ReferenceValueTemplate(PathTemplate(path))
        else:
            return PrimitiveValueTemplate(tmpl)
    else:
        return PrimitiveValueTemplate(tmpl)

class ValueTemplate(object):
    pass

class ObjectValueTemplate(ValueTemplate):

    def __init__(self):
        self.values = []

    def render(self, context):
        result = {}
        for n, v in self.values:
            for name, subctx in n.render(context):
                val = v.render(subctx)
                if val is None:
                    if name in result:
                        del result[name]
                else:
                    result[name] = v.render(subctx)
        return result

    def put(self, n, v):
        self.values.append((n, v))

class ArrayValueTemplate(ValueTemplate):

    def __init__(self):
        self.values = []

    def render(self, context):
        return [ v.render(context) for v in self.values ]

    def append(self, v):
        self.values.append(v)

class PrimitiveValueTemplate(ValueTemplate):

    def __init__(self, value):
        self.value = value

    def render(self, context):        
        return self.value

class ReferenceValueTemplate(ValueTemplate):

    def __init__(self, path_template):
        self.path = path_template

    def render(self, context):
        return context.get_value(self.path)

class NameTemplate(object):

    def __init__(self, name_template, path_template=None):                        
        self.path_template = path_template
        self.name_template = name_template

    def render(self, context):
        if self.path_template is None:
            yield context.render_string(self.name_template), context
        else:
            for subctx in context.match(self.path_template):
                name = subctx.render_string(self.name_template)
                yield name, subctx

class Placeholder(object):

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return "{%s}" % self.name

    def render(self, context):
        return context.get_var(self.name)

def parse_path(path):
    p = path.split("/")
    if len(p) == 0:
        return p
    if p[0] == "":
        p = p[1:]
    if len(p) == 0:
        return p
    if p[-1] == "":
        p = p[:-1]
    if len(p) == 0:
        return p
    return [ Placeholder(i[1:-1]) if len(i) >= 2 and i[0] == "{" and i[-1] == "}" else i for i in p ]                

class PathTemplate(object):

    def __init__(self, path):
        self.items = parse_path(path)

    def render(self, context):
        return [s.render(context) if type(s) == Placeholder else s for s in self.items]

def parse_str(d):
    result = []
    i = d.find("{")
    s = 0
    while i != -1:
      result.append(d[s:i])
      j = d.find("}", i+1)
      if j == -1:
        raise ValueError("Invalid key def: %s" % d)
      else:
        n = d[i+1:j]
        result.append(Placeholder(n))
        s = j+1
        i = d.find("{", s)
    result.append(d[s:])
    return result

class StrTemplate(object):

    def __init__(self, template):
        self.template = parse_str(template)

    def render(self, context):
        result = ""
        for s in self.template:
            if type(s) == str:
                result += s
            elif type(s) == Placeholder:
                result += s.render(context)
            else:
                assert False
        return result

def _match(path_template_arr, root, variables):
    #print "_match: %s" % (path_template_arr)
    i = 0
    while i < len(path_template_arr) and type(path_template_arr[i]) == str:
        i += 1
    if i > 0:
        root = root.subdocument(path_template_arr[:i])
    if i >= len(path_template_arr):
        #print "==> %s" % root
        yield Context(root, variables)
    else:
        for name, child in root.children():
            subctx = variables.copy()
            assert type(path_template_arr[i]) == Placeholder
            subctx[path_template_arr[i].name] = name
            for ctx in _match(path_template_arr[i+1:], child, subctx):
                #print "==> %s" % ctx.root
                yield ctx

class Context(object):

    def __init__(self, root, variables):
        self.root = root        
        self.variables = variables

    def get_var(self, name):
        return self.variables[name]

    def render_string(self, name_template):
        return name_template.render(self)

    def get_value(self, path_template):
        return self.root.get_value(path_template.render(self))

    def match(self, path_template):
        for ctx in _match(path_template.items, self.root, self.variables):
            yield ctx

class DictDocument(object):

    def __init__(self, d):
        self.val = d

    def get_value(self, path):
        d = self.val
        for s in path:
            if s == ".":
                pass
            else:
                try:
                    d = d[s]
                except KeyError:
                    return None
        return d

    def subdocument(self, path):
        return DictDocument(self.get_value(path))

    def children(self):
        if self.val is None or not isinstance(self.val, dict):
            return []
        else:
            return [(n, DictDocument(v)) for n, v in self.val.iteritems()]

    def __repr__(self):
        return json.dumps(self.val, indent=2)

if __name__ == "__main__":

    import json
    import sys
    import yaml

    with open(sys.argv[1]) as fp:
        tmpl = yaml.load(fp)

    with open(sys.argv[2]) as fp:
        input_doc = json.load(fp)        

    result = TreeParser(tmpl).render(DictDocument(input_doc))
    print result
    print json.dumps(result, indent=2)

    