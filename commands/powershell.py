import sys
import os

parameters = ' '.join(sys.argv[1:])
os.system(f'powershell -Command "{parameters}"')