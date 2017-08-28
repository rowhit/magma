from .port import INPUT, OUTPUT, INOUT
from .array import Array
from .conversions import array
from .circuit import AnonymousCircuit
from .wire import wire

__ALL__  = ['compose']
__ALL__ += ['curry', 'uncurry']
__ALL__ += ['row', 'col', 'map_']
__ALL__ += ['fork', 'join', 'flat']
__ALL__ += ['fold', 'scan']
__ALL__ += ['braid']

# flatten list of lists
def flatten(l):
    return sum(l, [])

# return a list of all the arguments 
# with a given name from a list of interfaces
def getarg(arg, interfaces):
    return [i.ports[arg] for i in interfaces]

def getdirection(args):
    a = args[0]
    if isinstance(a, list):
        a = a[0]
    if a.isinput():  return INPUT
    if a.isoutput(): return OUTPUT
    if a.isinout():  return INOUT
    return None

# return a list of all the arguments 
# in a given direction from a list of interfaces
def getargbydirection(interface, direction):
    args = []
    for name, port in interface.ports.items():
        if port.isoriented(direction):
            args.append(name)
    return args

#
def lscanarg(iarg, oarg, interfaces, noiarg=False, nooarg=False):
    iargs = getarg(iarg, interfaces)
    oargs = getarg(oarg, interfaces)
    n = len(interfaces)
    for i in range(n-1):
        wire(oargs[i], iargs[i+1])

    args = []
    if not noiarg:
        args += [iarg, iargs[0]]
    if not nooarg:
        args += [oarg, array(oargs)]
    return args

#
def rscanarg(iarg, oarg, interfaces, noiarg=False, nooarg=False):
    iargs = getarg(iarg, interfaces)
    oargs = getarg(oarg, interfaces)
    n = len(interfaces)
    for i in range(n-1):
        wire(oargs[i+1], iargs[i])

    args = []
    if not noiarg:
        args += [iarg, iargs[0]]
    if not nooarg:
        args += [oarg, array(oargs)]
    return args

#
def lfoldarg(iarg, oarg, interfaces, noiarg=False, nooarg=False):
    iargs = getarg(iarg, interfaces)
    oargs = getarg(oarg, interfaces)
    n = len(interfaces)
    for i in range(n-1):
        wire(oargs[i], iargs[i+1])
    args = []
    if not noiarg:
        args += [iarg, iargs[0]]
    if not nooarg:
        args += [oarg, oargs[n-1]]
    return args

def rfoldarg(iarg, oarg, interfaces, noiarg=False, nooarg=False):
    iargs = getarg(iarg, interfaces)
    oargs = getarg(oarg, interfaces)
    n = len(interfaces)
    for i in range(n-1):
        wire(oargs[i+1], iargs[i])
    args = []
    if not noiarg:
        args += [iarg, iargs[0]]
    if not nooarg:
        args += [oarg, oargs[n-1]]
    return args

# return [arg, args] from a list of interfaces
def forkarg(arg, interfaces):
    iargs = getarg(arg, interfaces)
    oarg = type(iargs[0])() # create a single anonymous value 
    for iarg in iargs:
         wire(oarg, iarg) # wire the anonymous value to all the forked args
    return [arg, oarg]

# return [arg, array] from a list of interfaces
def joinarg(arg, interfaces):
    args = getarg(arg, interfaces)
    #direction = getdirection(args)
    #print('joinarg', args)
    return [arg, array(args)]

# return [arg, array] from a list of interfaces
def flatarg(arg, interfaces):
    args = getarg(arg, interfaces)
    #direction = getdirection(args)
    #print('flatarg', args)
    flatargs = []
    for a in args:
        for i in range(len(a)):
            flatargs.append(a[i])
    return [arg, array(flatargs)]


# all powerful braid functions
#
#  circuits : list of circuits which should all have the same signature
#
#  forkargs : list of argument names to fork
#   this argument is wired to all the circuits
#  joinargs : list of argument names to join
#   this argument is equal an array of all the arguments from circuits
#  flatargs : list of argument names to flatten
#   this argument is equal an array of all the flatted arguments from circuits
#  foldargs : dict of argument namein:nameout, set namein[i+1] to namout[u]
#  rfoldargs : dict of argument namein:nameout, set namein[i-1] to namout[u]
#    namein[0] is retained in the result, 
#    nameout[n-1] is retained in the result
#  scanargs : dict of argument namein:nameout, set namein[i+1] to namout[u]
#  rscanargs : dict of argument namein:nameout, set namein[i-1] to namout[u]
#    namein[0] is retained in the result, 
#    the array nameout is retained in the result
#
# by default, clock arguments are forked,
#  unless they appear in another keyword
#
# by default, any arguments not appearing in a keyword are joined
#
def braid(circuits, 
            forkargs=[],
            joinargs=[],
            flatargs=[],
            foldargs={}, rfoldargs={},
            scanargs={}, rscanargs={}):

    forkargs = list(forkargs)

    interfaces = [circuit.interface for circuit in circuits]

    # by default, clkargs are added to forkargs,
    # unless they appear in another keyword
    for clkarg in interfaces[0].clockargnames():
        if clkarg in forkargs: continue
        if clkarg in joinargs: continue
        if clkarg in flatargs: continue
        if clkarg in foldargs.keys(): continue
        if clkarg in rfoldargs.keys(): continue
        if clkarg in scanargs.keys(): continue
        if clkarg in rscanargs.keys(): continue
        forkargs.append(clkarg)

    # do NOT join arguments if they appear in another keyword
    nojoinargs = forkargs + flatargs
    nojoinargs += flatten( [[k, v] for k, v in foldargs.items()] )
    nojoinargs += flatten( [[k, v] for k, v in rfoldargs.items()] )
    nojoinargs += flatten( [[k, v] for k, v in scanargs.items()] )
    nojoinargs += flatten( [[k, v] for k, v in rscanargs.items()] )

    joinargs = [name for name in interfaces[0].ports.keys() \
                    if name not in nojoinargs]

    #print('fork', forkargs)
    #print('flat', flatargs)
    #print('join', joinargs)
    #print('fold', foldargs)
    #print('scan', scanargs)
    args = []
    for key in interfaces[0].ports.keys():
        if   key in foldargs:
            iarg = key
            oarg = foldargs[key]
            noiarg = iarg in forkargs or iarg in joinargs
            nooarg = oarg in joinargs
            #print('lfolding', iarg, key, noiarg, nooarg)
            args += lfoldarg(iarg, oarg, interfaces, noiarg, nooarg)
        elif key in rfoldargs:
            iarg = key
            oarg = rfoldargs[key]
            #print('rfolding', iarg, key)
            noiarg = iarg in forkargs or iarg in joinargs
            nooarg = oarg in joinargs
            args += rfoldarg(iarg, oarg, interfaces, noiarg, nooarg)

        elif key in scanargs:
            iarg = key
            oarg = scanargs[key]
            #print('scanning', iarg, key)
            noiarg = iarg in forkargs or iarg in joinargs
            nooarg = oarg in joinargs
            args += lscanarg(iarg, oarg, interfaces, noiarg, nooarg)
        elif key in rscanargs:
            iarg = key
            oarg = rscanargs[key]
            #print('scanning', iarg, key)
            noiarg = iarg in forkargs or iarg in joinargs
            nooarg = oarg in joinargs
            args += rscanarg(iarg, oarg, interfaces, noiarg, nooarg)

        elif key in forkargs:
            #print('forking', key)
            args += forkarg(key, interfaces)

        elif key in joinargs:
            #print('joining', key)
            args += joinarg(key, interfaces)

        elif key in flatargs:
            #print('flattening', key)
            args += flatarg(key, interfaces)

    #print(args)
    return AnonymousCircuit(args)

# fork all inputs
def fork(*circuits):
    """Wire input to all the inputs, concatenate output"""
    if len(circuits) == 1: circuits = circuits[0]
    forkargs = getargbydirection(circuits[0].interface, INPUT)
    return braid(circuits, forkargs=forkargs)

# join all inputs
def join(*circuits):
    """concatenate input and concatenate output"""
    if len(circuits) == 1: circuits = circuits[0]
    return braid(circuits)

# flatten the join of all inputs - each input must be an array
#  should this operate on a single circuit
def flat(*circuits):
    if len(circuits) == 1: circuits = circuits[0]
    flatargs = getargbydirection(circuits[0].interface, INPUT)
    return braid(circuits, flatargs=flatargs)


def fold(*circuits, **kwargs):
    """fold"""
    if len(circuits) == 1: circuits = circuits[0]
    return braid(circuits, **kwargs)

def scan(*circuits, **kwargs):
    """scan"""
    if len(circuits) == 1: circuits = circuits[0]
    return braid(circuits, **kwargs)



def inputargs(circuit):
    return circuit.interface.inputargs()

def outputargs(circuit):
    return circuit.interface.outputargs()

# wire the outputs of circuit2 to the inputs of circuit1
def compose(circuit1, circuit2):
    wire(circuit2, circuit1)
    return AnonymousCircuit( inputargs(circuit2) + outputargs(circuit1) )


#
# curry a circuit
#
#  the input argument named prefix, which must be an array,
#  is broken into separate input arguments 
#
#  for example, if prefix='I',
#    then "I", array([i0, i1]) -> "I0", i0, "I1", i1 
#
# all other inputs remain unchanged
#
def curry(circuit, prefix='I'):
    args = []
    for name, port in circuit.interface.ports.items():
        if name == prefix and port.isinput():
           for i in range(len(port)):
               args.append('{}{}'.format(name, i))
               args.append(port[i])
        else:
           args.append(name)
           args.append(port)

    #print(args)
    return AnonymousCircuit(args)



def inputs(circuit):
    input = circuit.interface.inputs()
    if len(input) == 1:
        return input[0]
    else:
        return array(input)

def outputs(circuit):
    output = circuit.interface.outputs()
    if len(output) == 1:
        return output[0]
    else:
        return Array(*output)

#
# uncurry a circuit
#
#  all input arguments whose names begin with prefix 
#  are collected into a single input argument named prefix,
#  which is an array constructed from of the input arguments
#
#  for example, if prefix='I',
#    then "I0", i0, "I1", i1 -> "I", array([i0, i1])
#
#  the uncurry argument is the first argument in the result
#
# all other inputs remain unchanged.
#
def uncurry(circuit, prefix='I'):

    otherargs = []
    uncurryargs = []
    for name, port in circuit.interface.ports.items():
        # should we insert the argument in the position of the first match?
        if name.startswith(prefix) and port.isinput():
           uncurryargs.append(port)
        else:
           otherargs += [name, port]

    return AnonymousCircuit( [prefix, array(uncurryargs)] + otherargs )


def row(f, n):
    return [f(x) for x in range(n)]

def col(f, n):
    return [f(y) for y in range(n)]

def map_(f, n):
    return [f() for _ in range(n)]