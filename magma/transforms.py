from collections import namedtuple, OrderedDict
from .circuit import *
from .scope import *
from .bit import *
from .array import *
from .wire import wire, wiredefaultclock
from .ref import DefnRef, InstRef, ArrayRef

__all__ = ['TransformedCircuit', 'flatten', 'setup_clocks']

# Holds the new modified circuit as well as a map from old bits and scopes to
# new bits
class TransformedCircuit:
    def __init__(self, orig_circuit, transform_name):
        # Maps from original bits to bits in transformed circuit
        self.orig_to_new = {}
        self.circuit = DefineCircuit(orig_circuit.name + '_' + transform_name,
                                     *orig_circuit.interface.decl())
        EndCircuit()

    def get_new_bit(self, orig_bit, scope):
        return self.orig_to_new[QualifiedBit(bit=orig_bit, scope=scope)]

    def set_new_bit(self, orig_bit, orig_scope, new_bit):
        assert isinstance(new_bit, BitType) or isinstance(new_bit, ArrayType)

        if isinstance(orig_bit, ArrayType):
            # Also map the individual bits
            for o, n in zip(orig_bit, new_bit):
                self.orig_to_new[QualifiedBit(bit=o, scope=orig_scope)] = n

        self.orig_to_new[QualifiedBit(bit=orig_bit, scope=orig_scope)] = new_bit

def get_primitives(outer_circuit, outer_scope):
    primitives = []
    mapping = {}

    for instance in outer_circuit.instances:
        inner_scope = Scope(parent=outer_scope, instance=instance)
        inner_circuit = type(instance)

        if isprimitive(inner_circuit):
            primitives.append(QualifiedInstance(instance=instance, scope=outer_scope))
        else:
            for name, outerbit in instance.interface.ports.items():
                innerbit = inner_circuit.interface.ports[name]
                outerloc = QualifiedBit(bit=outerbit, scope=outer_scope)
                innerloc = QualifiedBit(bit=innerbit, scope=inner_scope)

                if isinstance(outerbit, ArrayType):
                    for o, i in zip(outerbit, innerbit):
                        oqual = QualifiedBit(bit=o, scope=outer_scope)
                        iqual = QualifiedBit(bit=i, scope=inner_scope)
                        if o.isinput():
                            mapping[iqual] = oqual
                        else:
                            mapping[oqual] = iqual

                if outerbit.isinput():
                    mapping[innerloc] = outerloc
                else:
                    mapping[outerloc] = innerloc

            instance_primitives, inst_map = get_primitives(inner_circuit, inner_scope)

            for k, v in inst_map.items():
                mapping[k] = v

            primitives += instance_primitives

    return (primitives, mapping)

def get_new_source(source_qual, primitive_map, old_circuit, new_circuit):
    old_source = source_qual.bit
    scope = source_qual.scope

    if old_source.const():
        return old_source

    bitref = old_source.name
    arrayref = isinstance(bitref, ArrayRef)
    if arrayref:
        idx = bitref.index
        bitref = bitref.array.name

    if isinstance(bitref, InstRef):
        # Get the primitive outbit is attached to,
        old_primitive = bitref.inst
        assert isprimitive(type(old_primitive)), "Failed to collapse bit to primitive"
        new_primitive = primitive_map[QualifiedInstance(instance=old_primitive, scope=scope)]
        newsource = new_primitive.interface.ports[bitref.name]
    elif isinstance(bitref, DefnRef):
        defn = bitref.defn
        assert defn == old_circuit.name, "Collapsed bit to circuit other than outermost"
        newsource = new_circuit.interface.ports[bitref.name]
    elif isinstance(old_source, ArrayType):
        # Must not be a whole array
        assert bitref.anon()

        new_source_array = []
        for s in old_source:
            partial_qual = QualifiedBit(bit=s, scope=scope)
            ns = get_new_source(partial_qual, primitive_map, old_circuit, new_circuit)
            new_source_array.append(ns)

        return array(*new_source_array)
    else:
        assert False, "Failed to collapse bit"

    if arrayref:
        newsource = newsource[idx]

    return newsource

def wire_new_bit(origbit, newbit, cur_scope, primitive_map, bit_map, old_circuit, flattened_circuit):
    # Trace back from origbit to it's source, tracking bits that will be "collapsed"
    new_circuit = flattened_circuit.circuit

    sourcebit = origbit.value()
    source_qual = QualifiedBit(bit=sourcebit, scope=cur_scope)
    orig_qual = QualifiedBit(bit=origbit, scope=cur_scope)
    collapsed_out_bits = [source_qual]
    collapsed_in_bits = [orig_qual]

    while source_qual in bit_map:
        intermediate_in = bit_map[source_qual]
        sourcebit = intermediate_in.bit.value()
        assert sourcebit is not None

        source_qual = QualifiedBit(bit=sourcebit, scope=intermediate_in.scope)
        collapsed_out_bits.append(source_qual)
        collapsed_in_bits.append(intermediate_in)

    newsource = get_new_source(source_qual, primitive_map, old_circuit, new_circuit)
    wire(newsource, newbit)

    for collapsed in collapsed_in_bits:
        flattened_circuit.set_new_bit(collapsed.bit, collapsed.scope, newbit)

    for collapsed in collapsed_out_bits:
        flattened_circuit.set_new_bit(collapsed.bit, collapsed.scope, newsource)

def flatten(circuit):
    flattened_circuit = TransformedCircuit(circuit, 'flattened')

    outer_scope = Scope()
    orig_primitives, bit_map = get_primitives(circuit, outer_scope)

    primitive_map = {} # Maps from primitives in the old circuit to new circuits
    new_primitives = []
    for old in orig_primitives:
        new = CopyInstance(old.instance)
        new_primitives.append(new)
        primitive_map[old] = new

    # Wire up all the new instances
    for new_inst, qual_inst in zip(new_primitives, orig_primitives):
        orig_inst = qual_inst.instance

        for name, origbit in orig_inst.interface.ports.items():
            if origbit.isinput():
                newbit = new_inst.interface.ports[name]
                wire_new_bit(origbit, newbit, qual_inst.scope, primitive_map, bit_map, circuit, flattened_circuit)

    # Finally, wire up the circuit outputs
    new_circuit = flattened_circuit.circuit
    for name, origbit in circuit.interface.ports.items():
        if origbit.isinput(): # Circuit output
            newbit = new_circuit.interface.ports[name]
            wire_new_bit(origbit, newbit, Scope(), primitive_map, bit_map, circuit, flattened_circuit)

    for primitive in new_primitives:
        new_circuit.place(primitive)

    return flattened_circuit

def get_uniq_children(circuit, circuits):
    name = circuit.__name__
    if not isdefinition(circuit):
        return circuits
    for i in circuit.instances:
        get_uniq_children(type(i), circuits)
    if name not in circuits:
        circuits[name] = circuit
    return circuits

def setup_clocks(main):
    # This should probably return a TransformedCircuit
    circuits = get_uniq_children(main, OrderedDict()).values()
    for circuit in circuits:
        for inst in circuit.instances:
            wiredefaultclock(circuit, inst)