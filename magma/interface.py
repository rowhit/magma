from __future__ import division
from collections import OrderedDict
from .ref import AnonRef, InstRef, DefnRef
from .t import *
from .port import *
from .bit import *
from .array import *
from .tuple import TupleType
from .compatibility import IntegerTypes, StringTypes

__all__  = ['DeclareInterface']
__all__ += ['Interface']

#
# parse argument declaration of the form 
#
#  (name0, type0, name1, type1, ..., namen, typen)
#
def parse(decl):
    #print(decl)
    n = len(decl)
    assert n % 2 == 0

    directions = []
    names = []
    ports = []
    for i in range(0,n,2):
        name = decl[i]   # name
        port = decl[i+1] # type

        assert isinstance(port, Kind) or isinstance(port, Type)

        direction = None
        if   port.isinput():  direction = INPUT
        elif port.isoutput(): direction = OUTPUT
        elif port.isinout():  direction = INOUT

        if direction is None:
            print("Error:", name, "must have a direciton")

        directions.append(direction)
        names.append(name)
        ports.append(port)

    return directions, names, ports

#
# Abstract Base Class for an Interface
#
class _Interface(Type):

    def __str__(self):
        return str(type(self))

    def __repr__(self):
        s = ""
        for input in self.inputs():
            output = input.value()
            if isinstance(output, ArrayType) or isinstance(output, TupleType):
                if not output.iswhole(output.ts):
                    for i in range(len(input)):
                        iname = repr( input[i] )
                        oname = repr( output[i] )
                        #assert input[i].debug_info == output[i].debug_info
                        #s += 'wire({}, {})  # {} {}\n'.format(oname, iname, *input[i].debug_info)
                        s += 'wire({}, {})\n'.format(oname, iname)
            else:
                iname = repr( input )
                oname = repr( output )
                #s += 'wire({}, {})  # {} {}\n'.format(oname, iname, *input.debug_info)
                s += 'wire({}, {})\n'.format(oname, iname)
        return s

    def __len__(self):
        return len(self.ports.keys())
                
    def __getitem__(self, key):
        if isinstance(key,slice):
            return array([self[i] for i in range(*key.indices(len(self)))])
        else:
            n = len(self)
            assert -n < key and key < len(self), "key: %d, self.N: %d" %(key,len(self))
            return self.arguments()[key]

    def inputs(self):
        input = []
        for name, port in self.ports.items():
            if port.isinput():
                if name in ['RESET', 'SET', 'CE', 'CLK', 'CIN']: 
                    continue
                input.append(port)
        return input

    def outputs(self):
        l = []
        for name, port in self.ports.items():
            if port.isoutput():
                if name in ['COUT']: 
                    continue
                l.append(port)
        return l

    def arguments(self):
        l = []
        for name, port in self.ports.items():
            l.append(port)
        return l

    def inputargs(self):
        l = []
        for name, port in self.ports.items():
            if port.isinput():
                if name in ['RESET', 'SET', 'CE', 'CLK', 'CIN']: 
                    continue
                l.append('%s' % name)
                l.append(port)
        return l

    def outputargs(self):
        l = []
        for name, port in self.ports.items():
            if port.isoutput():
                if name in ['COUT']: 
                    continue
                l.append('%s' % name)
                l.append(port)
        return l

    def clockargs(self):
        l = []
        for name, port in self.ports.items():
            if name in ['RESET', 'SET', 'CE', 'CLK']: 
                l.append('%s' % name)
                l.append(port)
        return l

    def args(self):
        l = []
        for name, port in self.ports.items():
            l.append('%s' % name)
            l.append(port)
        return l

    def decl(self):
        d = []
        for name, port in self.ports.items():
            d  += [name, type(port).flip()]
        return d

    def isclocked(self):
        for name, port in self.ports.items():
            if name in ['RESET', 'SET', 'CE', 'CLK']: 
                return True
        return False

#
# Interface class
#
# This function assumes the port instances are provided
#
#  e.g. Interface('I0', In(Bit)(), 'I1', In(Bit)(), 'O', Out(Bit)())
#
class Interface(_Interface):
    def __init__(self, decl):

        directions, names, ports = parse(decl)

        # setup ports
        args = OrderedDict()

        for i in range(len(directions)):
            direction = directions[i]
            name = names[i]
            port = ports[i]

            if isinstance(name, IntegerTypes):
                name = str(name)

            args[name] = port

        self.ports = args


#
# _DeclareInterface class
#
# First, an Interface is declared
#
#  Interface = DeclareInterface('I0', In(Bit), 'I1', In(Bit), 'O', Out(Bit))
#
# Then, the interface is instanced
#
#  interface = Interface()
#
class _DeclareInterface(_Interface):
    def __init__(self, inst=None, defn=None):

        # parse the class Interface declaration
        directions, names, ports = parse(self.Decl)

        args = OrderedDict()

        for i in range(len(directions)):
            direction = directions[i]
            name = names[i]
            port = ports[i]

            if defn:
               if   direction == OUTPUT: direction = INPUT
               elif direction == INPUT:  direction = OUTPUT
               elif direction == INOUT:  direction = INOUT

            if   inst: ref = InstRef(inst, name)
            elif defn: ref = DefnRef(defn, name)
            else:      ref = AnonRef(name)

            port = port.qualify(direction)

            args[name] = port(name=ref)

        self.ports = args

class InterfaceKind(Kind):
    def __str__(cls):
        args = []
        for i, arg in enumerate(cls.Decl):
            if i % 2 == 0:
                args.append('"{}"'.format(arg))
            else:
                args.append(str(arg))
        return ', '.join(args)

    def __eq__(cls, rhs):
        if not isinstance(rhs, InterfaceKind): return False

        if cls.Decl != rhs.Decl: return False
        return True

    __ne__=Kind.__ne__
    __hash__=Kind.__hash__


#
# Interface factory
#
def DeclareInterface(*decl):
    name = '%s(%s)' % ('Interface', ', '.join([str(a) for a in decl]))
    #print('DeclareInterface', name)
    dct = dict(Decl=decl)
    return InterfaceKind(name, (_DeclareInterface,), dct)

