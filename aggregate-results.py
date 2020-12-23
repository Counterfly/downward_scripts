#! /usr/bin/env python3


import json
import logging
import os
import re
import sys

logging.root.handlers = []
logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)])

import pandas as pd
pd.set_option('precision', 10)
pd.options.display.float_format = '{:,.10f}'.format

EXPECTED_NUMBER_TRIALS = 10 # the number of iterations each algorithm runs (to compute an average over)

# Helper Functions
def atoi(text):
  return int(text) if text.isdigit() else text

def natural_keys(string_or_number):
  """
  by Scott S. Lawton <scott@ProductArchitect.com> 2014-12-11; public domain and/or CC0 license
  
  handles cases where simple 'int' approach fails, e.g.
  ['0.501', '0.55'] floating point with different number of significant digits
  [0.01, 0.1, 1]    already numeric so regex and other string functions won't work (and aren't required)
  ['elm1', 'Elm2']  ASCII vs. letters (not case sensitive)
  """
  
  def try_float(astring):
    try:
      return float(astring)
    except:
      return astring
  
  if isinstance(string_or_number, basestring):
    string_or_number = string_or_number.lower()
  
    if len(re.findall('[.]\d', string_or_number)) <= 1:
      # assume a floating point value, e.g. to correctly sort ['0.501', '0.55']
      # '.' for decimal is locale-specific, e.g. correct for the Anglosphere and Asia but not continental Europe
      return [try_float(s) for s in re.split(r'([\d.]+)', string_or_number)]
    else:
      # assume distinct fields, e.g. IP address, phone number with '.', etc.
      # caveat: might want to first split by whitespace
      # TBD: for unicode, replace isdigit with isdecimal
      return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_or_number)]
  else:
    # consider: add code to recurse for lists/tuples and perhaps other iterables
    return string_or_number

PROPERTY = {
  'coverage':       'coverage',
  'cost' :          'cost',
  'evaluated':      'evaluated',
  'evaluations':    'evaluations',
  'expansions':     'expansions',
  'generated':      'generated',
  'error':          'error',
  'search_time':    'search time',
}
ERROR_SIGNAL_NO_ERROR = 'none'  # Error


RUNS_DIRECTORY_PREFIX = 'run'
RUNS_PROPERTIES_FILE = 'properties'
RUNS_ERROR_FILE = 'run.err'
DELIMETER = ','
def main(directory_path):
  """
  Recursively find all directories that begin with RUNS_DIRECTORY_PREFIX
  Then find all RUN_PROPERTIES_FILE file under each of these directories,
  gather the statistics and output the aggregates to screen using DELIMETER
  """
  aggregator = Aggregator()

  dirs_with_errors = []
  property_files = []
  for tup in sorted(os.walk(directory_path)):
    match = re.search(".+%s[0-9]+" % (RUNS_DIRECTORY_PREFIX), tup[0], re.I)
    if match:
    #if RUNS_DIRECTORY_PREFIX in tup[0]:
      #for run_dir in sorted(tup[1]):
      for run_dir in [tup[0]]:
        #run_dir_path = os.path.join(tup[0], run_dir)
        run_dir_path = tup[0]
        for run in sorted(os.walk(run_dir_path)):
          property_file = os.path.join(run_dir_path, RUNS_PROPERTIES_FILE)
          property_files.append(property_file)
          aggregator.aggregate_data(property_file)
          if run == RUNS_ERROR_FILE:
            dirs_with_errors.append(run_dir_path)

  # Done processing
  if len(dirs_with_errors) > 0:
    loglevel = logging.ERROR
  else:
    loglevel = logging.INFO
  logging.log(loglevel, "Number of dir with Errors = %s.", len(dirs_with_errors))
  
  # Assert that runs are equal across algorithms
  aggregator.check_assertions()

  # Print stats
  #aggregator.print_stats_per_domain()
  aggregator.print_domain_averages()


class Aggregator:

  def __init__(self):
    self.stats_per_domain = {}
    self.previous = {}

  def get_property(self, prop):
    # raise exception if key DNE
    return self.properties[prop]

  def aggregate_data(self, json_file_name):
    # Load json file and read in as dict
    with open(json_file_name) as json_file:
      self.properties = json.load(json_file)
      if self.properties['nickname'] == '?':
          logging.warning("nickname is unknown in %s", json_file_name)

    # determine which domain the run is associated with
    domain = self.get_property('domain')
  
    # determine which instance in the domain
    domain_instance = self.get_property('problem')
 
    # determine which algorithm this run is associated with
    algorithm_id = self.get_property('nickname')  # There are a couple options for this
 
    stats = Statistics(algorithm_id)
  
    # Read from file until start of Statistics output
    # all info is in properties file which is already in dictionary format
    # parse properties file and read into memory into dict struct
  
    #error = self.get_property('error')
    error = False
    # Use default error (which is pass) stats.add_metric('error', 'none')
    #if error == ERROR_SIGNAL_NO_ERROR:
    try:
      properties = {} 
      # Get coverage
      coverage = self.get_property('coverage');
      stats.add_metric('coverage', int(coverage))

      # Get cost
      cost = 0
      if coverage == 1:
        cost = self.get_property('cost');
      stats.add_metric('cost', int(cost))

      # Get Evaluated States
      evaluated = self.get_property('evaluated')
      stats.add_metric('evaluated', int(evaluated))

      # Get number of unique Evaluations
      evaluations = self.get_property('evaluations')
      stats.add_metric('evaluations', int(evaluations))

      # Get number of Expanded states
      expansions = self.get_property('expansions')
      stats.add_metric('expansions', int(expansions))

      # Get number of generated states
      generated = self.get_property('generated')
      stats.add_metric('generated', int(generated))

      # Get time to complete search
      value = self.get_property('search time')
      stats.add_metric('search time', float(value))

    except KeyError as e:
      logging.exception("KeyError in Aggregate with coverage=%s in file %s", self.get_property('coverage'), json_file_name)
      if self.get_property('coverage') == 1:
        exit("Something is ACTUALLY wrong!!!!")
    finally:
      pass
      #stats.add_metric('error', error)

    # Update Stats for the domain
    if domain not in self.stats_per_domain:
        self.stats_per_domain[domain] = pd.DataFrame()


    #self.stats_per_domain[domain][domain_instance][algorithm_id] = stats
    #row_properties = {
    #  PROPERTIES['coverage']: coverage,
    #  PROPERTIES['cost']: cost,
    #  PROPERTIES['evaluated']: evaluated,
    #  PROPERTIES['evaluations']: evaluations,
    #  PROPERTIES['expansions']: expansions,
    #  PROPERTIES['generated']: generated,
    #  PROPERTIES['search_time']: search_time,
    #}

    row_properties = stats.dict_representation()
    # Add domain instance and algorithm in
    row_properties['instance'] = domain_instance
    row_properties['domain'] = domain
    row_properties['alg'] = algorithm_id

    for key, value in row_properties.items():
        # Need to create index for scalar values (so pd knows how many rows intended)
        row_properties[key] = [value]

    # Add row in dataframe with domain instance as row header
    row_df = pd.DataFrame.from_dict(row_properties)

    # Update domain data frame
    self.stats_per_domain[domain] = self.stats_per_domain[domain].append(row_df)
    # NOTE: we will get duplicates because there are 10 runs per domain instance


  def print_domain_averages(self):
      '''Print domain averages aross all multi-run instances per algorithm'''
      # Print one Dataframe per domain
      for domain, domain_df in self.stats_per_domain.items():
        # Retrieve data frame run by a specific algorithm
        #print(domain_df)
	      # Create a new data frame that lists the number of runs each (domain, instance, alg) group ran
       	df_num_runs_per_group = pd.DataFrame({ 'num_runs': domain_df.groupby(['domain', 'instance', 'alg']).size() }).reset_index()

        missing_trials = df_num_runs_per_group[df_num_runs_per_group['num_runs'] != EXPECTED_NUMBER_TRIALS]
        if not missing_trials.empty:
          logging.warning("Expected %s trials, but some algorithms do not have that many.", EXPECTED_NUMBER_TRIALS)
          print(missing_trials)
        num_runs = df_num_runs_per_group['num_runs'][0]
        for idx in range(1, len(df_num_runs_per_group)):
            assert num_runs == df_num_runs_per_group['num_runs'][idx],  "Not an equal number of runs per (domain, instance, algorithm) tuple"

        #logging.debug(domain_df.dtypes)
        #logging.debug(domain_df.groupby(['domain', 'instance', 'alg']).dtypes)

        # Prints the average per domain instance
        desired_df = domain_df[['domain', 'instance', 'alg', 'coverage']]
        #print desired_df.groupby(['domain', 'instance', 'alg']).mean()

        # Prints the average per domain
        print("===Averages per domain===")
        print(desired_df.groupby(['domain', 'alg']).mean())
        print("/\\/\\/\\/\\/\\/\\/\\")
        
        #for alg in set(domain_df['alg']):
        #  pass

  def print_stats_per_domain(self):
    """Prints the stats out by domain order"""
    for domain in sorted(self.stats_per_domain):
      #if 'grid' in domain:
      if True:
        print('')
        print(domain)
        for metric in sorted(Statistics.get_metrics()):
          arbitrary_key = self.stats_per_domain[domain].keys()[0]
          sorted_algorithms = self.stats_per_domain[domain][arbitrary_key].keys()
          sorted_algorithms.sort(key=natural_keys)

          # Special, remove this block beginning here
          #sorted_algorithms.remove('RRW_EXP_HFF')
          #sorted_algorithms.remove('RRW_Luby_HFF')
          #sorted_algorithms.append('RRW_EXP_HFF')
          #sorted_algorithms.append('RRW_Luby_HFF')
          # ENd special block

          print("-----")
          print(metric)
          #print("{}{}{}{}".format(os.linesep, metric, DELIMETER, DELIMETER.join([str(x) for x in sorted_algorithms])))
          print("{}{}".format(os.linesep, DELIMETER.join([str(x) for x in sorted_algorithms])))
          sorted_instances = self.stats_per_domain[domain].keys()
          sorted_instances.sort(key=natural_keys)
          for instance in sorted_instances:
            #results = [instance]
            results = []
            for alg in sorted_algorithms:
              stats = self.stats_per_domain[domain][instance][alg]
              results.append(stats.get_metric(metric))
            #print("{}{}{}".format(instance, DELIMETER, DELIMETER.join([str(x) for x in results])))
            print("{}".format(DELIMETER.join([str(x) for x in results])))

  def check_assertions(self):
    """Checks to make sure the number of stats objects is equal for each
       algorithm
    """
    return


class Algorithm:
  """Algorithm that is run within fast downward"""
  
  def __init__(self, id):
    self.id = id


class Statistics:
  """Stats object we want to aggregate"""

  # static class variable
  metric_defaults = {
    PROPERTY['coverage'] :      0,
    PROPERTY['cost'] :          0,
    PROPERTY['evaluated'] :     0,
    PROPERTY['evaluations'] :   0,
    PROPERTY['expansions'] :    0,
    PROPERTY['generated'] :     0,
    PROPERTY['search_time'] :   0,
    #PROPERTY['error'] :        'None',
  }

  @staticmethod
  def get_metrics():
    return Statistics.metric_defaults.keys()

  @staticmethod 
  def register_metric(metric, default_value):
    metric_defaults[metric] = default_value

  def __init__(self, algorithm_id):
    self.algorithm_id = algorithm_id
    self.metrics = self.metric_defaults.copy()

  def add_metric(self, metric, value):
    self.metrics[metric] = value

  def get_metric(self, metric):
    return self.metrics[metric]

  def output(self):
    DELIMETER = ','
    for metric in sorted(self.metrics):
      print("{}{}{}".format(metric, DELIMETER, self.metrics[metric]))

  def dict_representation(self):
    return self.metrics.copy()

if __name__ == '__main__':
  if len(sys.argv) != 2:
    print('Incorrect Number of args, expected 1 directory')
  else:
    main(sys.argv[1])
