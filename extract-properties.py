import json
import logging
import mmap
import os
import re
import sys

import subprocess


logging.root.handlers = []
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)])


def extract_number(line):
    ''' extract first number-sequence
    '''
    val = re.search(r'\d+', line).group()
    return val


def main(directory):
    output_log_files = []
    OUTPUT_FILENAME = 'output.log'
    # for root, dirnames, filenames in os.walk('./data/thesis3'):
    for root, dirnames, filenames in os.walk(directory):
        logging.debug("root = %s", root)
        logging.debug("dirnames = %s", dirnames)
        logging.debug("filenames = %s", filenames)
        for filename in filenames:
            if filename.lower() == OUTPUT_FILENAME.lower():
                output_log_files.append(
                    os.path.abspath(os.path.join(root, filename)))

    bool_regexes = {
        'Coverage':     r'Solution found\!',
    }
    capture_regexes = {
        'Nickname':     r'nickname: ([a-zA-Z0-9\.\_]+)',
        'Plan length':  r'Plan length: (\d+) step\(s\)',
        'Plan Cost':    r'Plan Cost\: (\d+)',
        'Cost':         r'Plan Cost\: (\d+)',
        'Expansions':   r'Expanded (\d+) state\(s\)',
        'Reopened':     r'Reopened (\d+) state\(s\)',
        'Evaluated':    r'Evaluated (\d+) state\(s\)',
        'Evaluations':  r'Evaluations\: (\d+)',
        'Generated':    r'Generated (\d+) state\(s\)',
        'Dead ends':    r'Dead ends\: (\d+) state\(s\)',
        # exclude .pddl
        'domain':       r'INFO.*\/benchmarks\/(.+)\/domain\.pddl',
        # include .pddl
        'problem':      r'INFO.*\/benchmarks\/.+\/(.*\d+.*\.pddl)',
        'search time':  r'Actual search time: ([0-9\.]+)s',
        'rng seed':     r'rng-random_seed: ([-\d]+)'
    }

    count = 0
    ERROR_STRING = 'Traceback (most recent call last)'
    for output_log_file in output_log_files:
        count += 1

        if count % 100 == 0:
            print("on %s" % output_log_file)

        results = {
            'coverage':     0,
            'nickname':     '?',
            'problem':      '?',
            'domain':       '?',
            'plan length':  0,
            'plan cost':    0,
            'cost':         0,    # duplicate of plan cost just for backward compatibility
            'expansions':   0,
            'reopened':     0,
            'evaluated':    0,
            'evaluations':  0,
            'generated':    0,
            'dead ends':    0,
            'search time':  0,
            'rng seed': 'Unknown',
            'error': '',
        }

        skipped_files = []
        error_files = []
        # Do pre-processing on file
        # Remove all lines containing the patterns
        was_empty = os.stat(output_log_file).st_size == 0
        subprocess.call(
            ["sed", "-i", "", "/new\ restart\_length/d", output_log_file])
        subprocess.call(
            ["sed", "-i", "", "/restart\ length/d", output_log_file])

        is_empty = os.stat(output_log_file).st_size == 0
        print("output_log_file = ", output_log_file, "is_empty=", is_empty)
        if is_empty:
            logging.warning("skipping %s", output_log_file)
            skipped_files.append((output_log_file, was_empty, is_empty))
            continue

        current_output_error_line_count = 0
        current_output_error_string = ''
        with open(output_log_file, 'r') as log_file:
            for line in log_file:
                for attribute, regex in bool_regexes.items():
                    match = re.search(regex, line, re.I)
                    if match:
                        # Override default value
                        results[attribute.lower()] = 1

                for attribute, regex in capture_regexes.items():
                    match = re.search(regex, line, re.I)
                    if match:
                        val = match.group(1)
                        results[attribute.lower()] = val
                        if 'HFF' in results['nickname']:
                            print(output_log_file)

                if current_output_error_line_count > 0:
                    current_output_error_string += f"{os.linesep}{line}"
                    current_output_error_line_count += 1
                    if current_output_error_line_count > 20:
                        current_output_error_string += f"{os.linesep}[DONE]"
                        current_output_error_line_count = 0
                elif ERROR_STRING.lower() in line.lower():
                    logging.warning("found error")
                    current_output_error_line_count += 1

        results['error'] = current_output_error_string
        if len(current_output_error_string) > 0:
            logging.warning("ERROR: %s", current_output_error_string)
            error_files.append(output_log_file)

        output_file = os.path.dirname(output_log_file) + '/properties'

        with open(output_file, 'w+') as outfile:
            json.dump(results, outfile)

    logging.info("skipped %d files: %s", len(skipped_files), skipped_files)
    logging.info("error %d files: %s", len(error_files), error_files)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Incorrect Number of args, expected 1 directory')
    else:
        main(sys.argv[1])
