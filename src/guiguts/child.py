# Child process test file
import sys

input_string = input()
print(f'Received "{input_string}"')
output_string = input_string.upper()
print(f'Output "{output_string}"')
print("This should appear in stderr", file=sys.stderr)
