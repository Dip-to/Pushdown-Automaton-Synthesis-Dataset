#!/usr/bin/env python3
"""
Complete PDA Parser and Validator
Reads formal PDA from input.txt, converts it to DPDA/NPDA, and runs test cases
Usage: python pda_complete.py [--visual]
"""

import argparse
import re
from typing import Dict, Set, Tuple, Union, List
from automata.pda.dpda import DPDA
from automata.pda.npda import NPDA


def parse_formal_pda(formal_text: str) -> Dict:
    """
    Parse formal PDA notation and extract components.
    
    Expected format:
    Q = {q0, q1, ...}
    Σ = {a, b, ...}
    Γ = {Z, A, ...}
    q₀ = q0
    Z₀ = Z
    F = {q3, ...}
    δ(state, input, stack_top) = (next_state, stack_op)
    """
    
    # Clean up the text
    formal_text = formal_text.strip()
    
    # Replace subscripts with regular characters
    formal_text = formal_text.replace('₀', '0').replace('₁', '1').replace('₂', '2').replace('₃', '3')
    
    result = {
        'states': set(),
        'input_symbols': set(),
        'stack_symbols': set(),
        'initial_state': None,
        'initial_stack_symbol': None,
        'final_states': set(),
        'transitions': {}
    }
    
    lines = formal_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Remove extra spaces around = sign
        line = re.sub(r'\s*=\s*', '=', line)
        
        # Parse Q = {q0, q1, ...}
        if line.startswith('Q='):
            result['states'] = parse_set(line)
        
        # Parse Σ = {a, b, ...}
        elif line.startswith('Σ=') or line.startswith('Sigma='):
            result['input_symbols'] = parse_set(line)
        
        # Parse Γ = {Z, A, ...}
        elif line.startswith('Γ=') or line.startswith('Gamma='):
            result['stack_symbols'] = parse_set(line)
        
        # Parse q₀ = q0 or q0 = q0
        elif re.match(r'q[₀0]=', line):
            result['initial_state'] = line.split('=')[1].strip()
        
        # Parse Z₀ = Z or Z0 = Z
        elif re.match(r'Z[₀0]=', line):
            result['initial_stack_symbol'] = line.split('=')[1].strip()
        
        # Parse F = {q3, ...}
        elif line.startswith('F='):
            result['final_states'] = parse_set(line)
        
        # Parse δ transitions
        elif line.startswith('δ(') or line.startswith('delta('):
            parse_transition(line, result['transitions'])
    
    return result


def parse_set(line: str) -> Set[str]:
    """Parse a set notation like {q0, q1, q2}"""
    match = re.search(r'\{([^}]*)\}', line)
    if match:
        content = match.group(1).strip()
        if not content:
            return set()
        # Split by comma and clean each element (strip whitespace and quotes)
        elements = [elem.strip().strip("'\"") for elem in content.split(',')]
        return set(elem for elem in elements if elem)
    return set()


def parse_transition(line: str, transitions: Dict) -> None:
    """
    Parse transition like: δ(q0, a, Z) = (q1, AZ)
    or δ(q0, ε, Z) = {(q1, Z), (q2, AZ)}
    """
    # Replace ε with empty string marker
    line = line.replace('ε', 'EPSILON').replace('epsilon', 'EPSILON')
    
    # Match pattern: δ(state, input, stack) = (next_state, stack_op) or = {(...), (...)}
    pattern = r'[δdelta]+\(([^,]+),\s*([^,]+),\s*([^)]+)\)\s*=\s*(.+)'
    match = re.match(pattern, line)
    
    if not match:
        return
    
    state = match.group(1).strip().strip("'\"")
    input_sym = match.group(2).strip().strip("'\"")
    stack_top = match.group(3).strip().strip("'\"")
    result = match.group(4).strip()
    
    # Convert EPSILON back to empty string
    if input_sym == 'EPSILON':
        input_sym = ''
    
    # Initialize state in transitions if not exists
    if state not in transitions:
        transitions[state] = {}
    
    if input_sym not in transitions[state]:
        transitions[state][input_sym] = {}
    
    # Check if result is a set (NPDA) or single tuple (DPDA)
    if result.startswith('{'):
        # NPDA: multiple transitions
        tuples = parse_transition_set(result)
        transitions[state][input_sym][stack_top] = tuples
    else:
        # DPDA: single transition
        next_state, stack_op = parse_transition_tuple(result)
        transitions[state][input_sym][stack_top] = (next_state, stack_op)


def parse_transition_set(text: str) -> Set[Tuple]:
    """Parse set of transitions like {(q1, AZ), (q2, Z)}"""
    # Remove outer braces
    text = text.strip('{}')
    
    # Find all tuples
    tuples = []
    pattern = r'\(([^,]+),\s*([^)]+)\)'
    
    for match in re.finditer(pattern, text):
        next_state = match.group(1).strip().strip("'\"")
        stack_op = parse_stack_operation(match.group(2).strip())
        tuples.append((next_state, stack_op))
    
    return set(tuples)


def parse_transition_tuple(text: str) -> Tuple[str, Union[str, Tuple]]:
    """Parse single transition like (q1, AZ)"""
    # Remove outer parentheses
    text = text.strip('()')
    
    # Split by comma (only first comma to handle stack ops)
    parts = text.split(',', 1)
    if len(parts) != 2:
        return ('', '')
    
    next_state = parts[0].strip().strip("'\"")
    stack_op = parse_stack_operation(parts[1].strip())
    
    return (next_state, stack_op)


def parse_stack_operation(stack_str: str) -> Union[str, Tuple]:
    """
    Parse stack operation string to appropriate format.
    Examples:
    - 'AZ' -> ('A', 'Z')
    - 'ε' or '' -> ''
    - 'Z' -> ('Z',)
    """
    stack_str = stack_str.strip().strip("'\"")
    
    # Handle epsilon/empty
    if stack_str in ('ε', 'EPSILON', 'epsilon', ''):
        return ''
    
    # Single symbol
    if len(stack_str) == 1:
        return (stack_str,)
    
    # Multiple symbols - convert to tuple (rightmost is top)
    return tuple(stack_str)


def is_npda(transitions: Dict) -> bool:
    """
    Determine if the PDA is non-deterministic based on transition structure.
    A PDA is non-deterministic if:
    1. Any transition maps to a set (multiple next states)
    2. There are epsilon transitions alongside symbol transitions for same state/stack
    3. Multiple transitions exist for the same (state, input, stack) combination
    """
    for state, state_trans in transitions.items():
        # Check if any result is a set (explicit non-determinism)
        for input_sym, stack_trans in state_trans.items():
            for stack_top, result in stack_trans.items():
                if isinstance(result, set):
                    return True
        
        # Check for epsilon transitions alongside symbol transitions
        # For each stack symbol, if there's an epsilon transition, 
        # check if there are also symbol transitions
        if '' in state_trans:  # Has epsilon transitions
            epsilon_stacks = set(state_trans[''].keys())
            
            # Check all other input symbols
            for input_sym, stack_trans in state_trans.items():
                if input_sym == '':  # Skip epsilon itself
                    continue
                
                # If any stack symbol appears in both epsilon and symbol transitions
                symbol_stacks = set(stack_trans.keys())
                if epsilon_stacks & symbol_stacks:  # Intersection is non-empty
                    return True
    
    return False


def create_pda_object(parsed: Dict):
    """Create DPDA or NPDA object from parsed data"""
    
    is_nondeterministic = is_npda(parsed['transitions'])
    
    if is_nondeterministic:
        # For NPDA, all transitions must be sets of tuples
        # Convert any plain tuples to sets
        normalized_transitions = {}
        for state, state_trans in parsed['transitions'].items():
            normalized_transitions[state] = {}
            for input_sym, stack_trans in state_trans.items():
                normalized_transitions[state][input_sym] = {}
                for stack_top, result in stack_trans.items():
                    if isinstance(result, set):
                        # Already a set, keep as is
                        normalized_transitions[state][input_sym][stack_top] = result
                    else:
                        # Plain tuple, convert to set
                        normalized_transitions[state][input_sym][stack_top] = {result}
        
        return NPDA(
            states=parsed['states'],
            input_symbols=parsed['input_symbols'],
            stack_symbols=parsed['stack_symbols'],
            transitions=normalized_transitions,
            initial_state=parsed['initial_state'],
            initial_stack_symbol=parsed['initial_stack_symbol'],
            final_states=parsed['final_states'],
            acceptance_mode='final_state'
        )
    else:
        return DPDA(
            states=parsed['states'],
            input_symbols=parsed['input_symbols'],
            stack_symbols=parsed['stack_symbols'],
            transitions=parsed['transitions'],
            initial_state=parsed['initial_state'],
            initial_stack_symbol=parsed['initial_stack_symbol'],
            final_states=parsed['final_states']
        )


def print_formal_pda(parsed: Dict):
    """Print the formal PDA definition"""
    print("\n" + "=" * 60)
    print("FORMAL PDA DEFINITION")
    print("=" * 60)
    print(f"Q = {{{', '.join(sorted(parsed['states']))}}}")
    print(f"Σ = {{{', '.join(sorted(parsed['input_symbols']))}}}")
    print(f"Γ = {{{', '.join(sorted(parsed['stack_symbols']))}}}")
    print(f"q₀ = {parsed['initial_state']}")
    print(f"Z₀ = {parsed['initial_stack_symbol']}")
    print(f"F = {{{', '.join(sorted(parsed['final_states']))}}}")
    print("\nδ: Q × (Σ ∪ {ε}) × Γ → Q × Γ*")
    
    for state in sorted(parsed['transitions'].keys()):
        for input_sym in sorted(parsed['transitions'][state].keys()):
            for stack_top, result in parsed['transitions'][state][input_sym].items():
                input_display = 'ε' if input_sym == '' else input_sym
                if isinstance(result, set):
                    for r in result:
                        next_state, stack_op = r
                        stack_display = 'ε' if stack_op == '' else ''.join(stack_op) if isinstance(stack_op, tuple) else stack_op
                        print(f"δ({state}, {input_display}, {stack_top}) = ({next_state}, {stack_display})")
                else:
                    next_state, stack_op = result
                    stack_display = 'ε' if stack_op == '' else ''.join(stack_op) if isinstance(stack_op, tuple) else stack_op
                    print(f"δ({state}, {input_display}, {stack_top}) = ({next_state}, {stack_display})")
    print("=" * 60)


def validate_pda_loops(parsed: Dict) -> None:
    """
    Check for obvious infinite loops (Direct Epsilon Self-Loops).
    Raises Exception if a loop is detected.
    """
    transitions = parsed['transitions']
    
    for state, state_trans in transitions.items():
        if '' in state_trans:  # Has epsilon transitions
            for stack_top, result in state_trans[''].items():
                
                # Helper to check a single transition tuple
                def is_loop(next_st, op):
                    # Check if next state is same
                    if next_st != state:
                        return False
                    
                    # Check if stack operation is identity (pushing same symbol back)
                    # parse_stack_operation returns tuple e.g. ('Z',) or string '' or tuple ('A', 'Z')
                    
                    # If op is single tuple ('Z',) matches stack_top 'Z'
                    if isinstance(op, tuple) and len(op) == 1 and op[0] == stack_top:
                        return True
                        
                    # If op is string/char equal to stack_top (unlikely given parser but possible)
                    if op == stack_top:
                        return True
                        
                    return False

                # Handle NPDA (set of results) vs DPDA (single result)
                if isinstance(result, set):
                    for r in result:
                        next_state, stack_op = r
                        if is_loop(next_state, stack_op):
                             raise Exception(f"Potential infinite loop detected: δ({state}, ε, {stack_top}) -> ({next_state}, {stack_top})")
                else:
                    next_state, stack_op = result
                    if is_loop(next_state, stack_op):
                        raise Exception(f"Potential infinite loop detected: δ({state}, ε, {stack_top}) -> ({next_state}, {stack_top})")



def generate_python_code(parsed: Dict) -> str:
    """Generate Python code for the PDA"""
    is_nondeterministic = is_npda(parsed['transitions'])
    pda_type = 'NPDA' if is_nondeterministic else 'DPDA'
    
    # Normalize transitions for NPDA
    transitions = parsed['transitions']
    if is_nondeterministic:
        normalized_transitions = {}
        for state, state_trans in transitions.items():
            normalized_transitions[state] = {}
            for input_sym, stack_trans in state_trans.items():
                normalized_transitions[state][input_sym] = {}
                for stack_top, result in stack_trans.items():
                    if isinstance(result, set):
                        normalized_transitions[state][input_sym][stack_top] = result
                    else:
                        normalized_transitions[state][input_sym][stack_top] = {result}
        transitions = normalized_transitions
    
    # Build the code
    code_lines = [f"pda = {pda_type}("]
    
    # States
    code_lines.append(f"    states={{{', '.join(repr(s) for s in sorted(parsed['states']))}}},")
    
    # Input symbols
    code_lines.append(f"    input_symbols={{{', '.join(repr(s) for s in sorted(parsed['input_symbols']))}}},")
    
    # Stack symbols
    code_lines.append(f"    stack_symbols={{{', '.join(repr(s) for s in sorted(parsed['stack_symbols']))}}},")
    
    # Transitions
    code_lines.append("    transitions={")
    for state in sorted(transitions.keys()):
        code_lines.append(f"        {repr(state)}: {{")
        for input_sym in sorted(transitions[state].keys()):
            code_lines.append(f"            {repr(input_sym)}: {{")
            for stack_top, result in transitions[state][input_sym].items():
                if isinstance(result, set):
                    # NPDA format
                    result_str = '{' + ', '.join(str(r) for r in sorted(result)) + '}'
                else:
                    # DPDA format
                    result_str = str(result)
                code_lines.append(f"                {repr(stack_top)}: {result_str},")
            code_lines.append("            },")
        code_lines.append("        },")
    code_lines.append("    },")
    
    # Initial state
    code_lines.append(f"    initial_state={repr(parsed['initial_state'])},")
    
    # Initial stack symbol
    code_lines.append(f"    initial_stack_symbol={repr(parsed['initial_stack_symbol'])},")
    
    # Final states
    code_lines.append(f"    final_states={{{', '.join(repr(s) for s in sorted(parsed['final_states']))}}},")
    
    # Add acceptance mode for NPDA
    if is_nondeterministic:
        code_lines.append("    acceptance_mode='final_state'")
    
    code_lines.append(")")
    
    return '\n'.join(code_lines)


def parse_test_cases(text: str) -> List[Tuple[str, bool]]:
    """
    Parse test cases from text.
    Format: ("string", "ACCEPT"/"REJECT") per line
    """
    test_cases = []
    
    # Process line by line
    lines = text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Pattern: ("string", "ACCEPT") or ("string", "REJECT")
        pattern = r'\("([^"]*)",\s*"(ACCEPT|REJECT)"\)'
        match = re.search(pattern, line)
        
        if match:
            string = match.group(1)
            expected = match.group(2) == 'ACCEPT'
            test_cases.append((string, expected))
    
    return test_cases


def main():
    parser = argparse.ArgumentParser(description='Parse PDA from input.txt and validate with test cases')
    parser.add_argument('--visual', action='store_true', help='Generate visualization')
    args = parser.parse_args()
    
    print("PDA Parser and Validator")
    print("=" * 60)
    
    # Read from input.txt file
    try:
        with open('input.txt', 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print("\nError: input.txt file not found!")
        print("Please create an input.txt file with your formal PDA definition.")
        return
    except Exception as e:
        print(f"\nError reading input.txt: {e}")
        return
    
    if not content.strip():
        print("\nError: input.txt is empty!")
        return
    
    # Split content into PDA definition and test cases
    # Look for test cases section
    parts = content.split('# Test Cases')
    if len(parts) == 1:
        parts = content.split('#Test Cases')
    if len(parts) == 1:
        parts = content.split('Test Cases:')
    
    formal_text = parts[0]
    test_cases_text = parts[1] if len(parts) > 1 else ""
    
    # Parse the formal PDA
    print("Parsing formal PDA from input.txt...")
    parsed = parse_formal_pda(formal_text)
    
    # Print formal definition
    print_formal_pda(parsed)

    # Check for infinite epsilon loops
    try:
        validate_pda_loops(parsed)
    except Exception as e:
        print(f"✗ Error creating PDA: {e}")
        return
    
    # Create PDA object
    pda_type = "NPDA" if is_npda(parsed['transitions']) else "DPDA"
    print(f"\nPDA Type: {pda_type}")
    
    try:
        pda = create_pda_object(parsed)
        print("✓ PDA created successfully!")
        print(pda)
    except Exception as e:
        print(f"✗ Error creating PDA: {e}")
        return
    
    # Generate and save Python code
    python_code = generate_python_code(parsed)
    try:
        with open('pda_output.py', 'w', encoding='utf-8') as f:
            f.write("from automata.pda.dpda import DPDA\n")
            f.write("from automata.pda.npda import NPDA\n\n")
            f.write(python_code)
        print("✓ Python code saved to pda_output.py")
    except Exception as e:
        print(f"✗ Error saving Python code: {e}")
    
    # Parse test cases if provided
    if test_cases_text.strip():
        test_cases = parse_test_cases(test_cases_text)
    else:
        # Default test cases if none provided
        print("\nNo test cases found in input.txt. Using default test cases.")
        test_cases = [
            ("", True),
            ("a", False),
            ("ab", True),
        ]
    
    # Run test cases
    print("\n" + "=" * 60)
    print("TESTING PDA")
    print("=" * 60)
    passed = 0
    
    for test_str, expected in test_cases:
        try:
            result = pda.accepts_input(test_str)
            status = "✓ PASS" if result == expected else "✗ FAIL"
            passed += (result == expected)
            print(f"{status} | '{test_str}' → {'ACCEPT' if result else 'REJECT'} (expected: {'ACCEPT' if expected else 'REJECT'})")
        except Exception as e:
            print(f"✗ ERROR | '{test_str}' → {e}")
    
    print("=" * 60)
    print(f"Results: {passed}/{len(test_cases)} passed\n")
    
    # Generate visualization if requested
    if args.visual:
        print("Generating visualizations...")
        try:
            pda.show_diagram(path='pda_diagram.svg', horizontal=True, fig_size=(12, 6))
            print("  ✓ pda_diagram.png (state diagram)")
        except Exception as e:
            print(f"  ✗ Error generating diagram: {e}")
        
        # Visualize first accepted test case
        for test_str, expected in test_cases:
            if expected:
                try:
                    pda.show_diagram(
                        input_str=test_str,
                        with_machine=True,
                        with_stack=True,
                        path=f'images/pda_execution_{test_str if test_str else "empty"}.png',
                        horizontal=True,
                        font_size=18.0,
                        arrow_size=1.0,
                        state_separation=1.5,
                        fig_size=(16, 10)
                    )
                    print(f"  ✓ pda_execution_{test_str if test_str else 'empty'}.png (execution trace)")
                except Exception as e:
                    print(f"  ✗ Error generating execution trace: {e}")
                    break


if __name__ == '__main__':
    main()