import subprocess
import sys
import pstats

from graphviz import Source

# Define the datetime string for filenames
datetime_string = "2024-10-31_20-09"

# Load the profiling data from the .prof file
profiler_stats = pstats.Stats(f'load_testing/{datetime_string}.prof')

# Print the top 10 functions sorted by time spent in the function (not including sub-functions)
print("Top 10 functions by time spent:")
profiler_stats.sort_stats('time').print_stats(10)

# Print the top 10 functions sorted by cumulative time spent (including sub-functions)
print("\nTop 10 functions by cumulative time spent:")
profiler_stats.sort_stats('cumulative').print_stats(10)

# Run gprof2dot to convert .prof file to DOT format using sys.executable
prof_file = f'load_testing/{datetime_string}.prof'
dot_file = f'load_testing/{datetime_string}.dot'
subprocess.run([
    sys.executable, '-m', 'gprof2dot', '-f', 'pstats',
    prof_file, '-o', dot_file
], check=True)

# Load the DOT file and render it as SVG
svg_filename = f'load_testing/{datetime_string}_flamegraph'
Source.from_file(dot_file).render(svg_filename, format='svg', cleanup=True)

print(f"Flamegraph saved as {svg_filename}")
