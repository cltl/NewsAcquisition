import requests
from collections import Counter
import operator

def show_me(main_dict, keys, headers, meta=set()):
    """
    this function shows in a html table
    for the keys of the main dict the headers (attributes)
    
    :param dict main_dict: either lex_expr_objs or ev_meaning_objs
    (see notebook 'Domain2lexical expression2event meanings.ipynb'
    :pararm iterable keys: keys from the main_dict to inspect
    :param list headers: the attribute you want to inspect from the keys
    :param set meta: keys for which you want to show:
    1. number of items
    2. minimum, average, and maximum
    
    :rtype: IPython.core.display.HTML
    :return: the results in a html table
    """ 
    rows = []
    for key in keys:
        if key not in main_dict:
            row = [key] + ['NA' for _ in range(len(headers)-1)]
            rows.append(row)
            continue
            
        the_object = main_dict[key]
        row = [getattr(the_object, header) for header in headers]
        rows.append(row)
    
    df = pandas.DataFrame(rows, columns=headers)
    
    if meta:
        print('number of rows: %s' % len(df))
        for key in meta:
            minimum = min(df[key])
            maximum = max(df[key])
            average = sum(df[key]) / len(df)
            print('%s: min(%s), avg(%s), max(%s)' % (key, 
                                                     minimum, 
                                                     round(average, 2),
                                                     maximum))
    
    table = tabulate(df, headers='keys', tablefmt='html')
    return table

def count_for_query(q):
    return extract_size(create_url_from_query(q))

def create_url_from_query(q, size=1):
    base = 'http://news.fii800.lod.labs.vu.nl/news?'
    args = {
    'q' : q, # the query terms to look for
    'in' : 'content', # look in title, content or both (supported values are: "title", "content", "both")
    'from' : '2010-09-01T00:00:00Z', # from->starting datetime point
    'to' : '2016-09-30T00:00:00Z', # ending datetime point
    'source' : '', # source -> which source
    'media' : 'News', # media -> media type ("Blog" or "News")
    'size' : size, # size -> amount of results to return
    'offset' : 0,  # offset ->skip the first offset results (useful for pagination)
    'match' : 'conjunct'
    }
    return create_url(base, args)

def create_url(base, args):
    """
    give the base url, add all arguments
    
    :param str base: base url
    :param dict args: mapping keyword argument to value
    
    :rtype: str
    :return: url
    """
    arguments = '&'.join(['%s=%s' % (key, value)
                          for key, value in args.items()
                          if value])
    
    url = ''.join([base, arguments])
    #print(url)
    return url


def extract_hits(url):
    """
    given an url:
    http://news.fii800.lod.labs.vu.nl/news?offset=0&to=2015-09-27T00:00:00Z&media=News&size=1000&from=2015-09-20T00:00:00Z&in=content&q=crash
    
    return all hits
    
    :param str url: the url that return json
    
    :rtype: dict
    :return: dict mapping hit identifier -> the info about each hit
    """
    response = requests.get(url)
    if response.status_code == 200:
        json = response.json()
        results = {hit['_source']['id']: hit
                   for hit in json['hits']['hits']}
    else:
        results = {}
        
    return results

def extract_size(url):
    """
    given an url:
    http://news.fii800.lod.labs.vu.nl/news?offset=0&to=2015-09-27T00:00:00Z&media=News&size=1&from=2015-09-20T00:00:00Z&in=content&q=crash
   
    return the number of hitss
   
    :param str url: the url that return json
   
    :rtype: int
    :return: int
    """
    response = requests.get(url)
    if response.status_code == 200:
        json = response.json()
        result_size = int(json['hits']['total'])
    else:
        result_size = 0
    
    return result_size
    
def get_all_hits(base, args):
    """
    
    given an url:
    http://news.fii800.lod.labs.vu.nl/news?offset=0&to=2015-09-27T00:00:00Z&media=News&size=1000&from=2015-09-20T00:00:00Z&in=content&q=crash
    
    return all hits using pagination
    
    :param str url: the url that return json
    :param dict args: mapping keyword argument to value

    :rtype: dict
    :return: dict mapping hit identifier -> the info about each hit
    """
    all_results = {}
    keep_going = True
    
    while keep_going:
        url = create_url(base, args)
        results = extract_hits(url)
        
        if results:
            all_results.update(results)
            
        else:
            keep_going = False
            
        args['offset'] += args['size']
            
    return all_results

def count_sources(results):
    """
    return frequency of each source
    
    :param dict results: mapping hit identifier -> the info about each hit
    
    :rtype: dict
    :return: source -> frequency
    """
    freq = Counter([value['_source']['source']
                    for value in results.values()])
    return freq

def print_first_x(d, limit=10):
    """
    print values with 10 highest values
    """
    for counter, (key, value) in enumerate(sorted(d.items(), 
                                                  key=operator.itemgetter(1),
                                                  reverse=True)):
        print(key, value)
        if counter == limit:
            break
    
def count_times(results):
    """
    return time frequency
    
    :param dict results: mapping hit identifier -> the info about each hit
    
    :rtype: dict
    :return: year -> frequency
    """
    dates = [value['_source']['published']
             for value in results.values()]
    
    freq = Counter([date.split('-')[0]
                    for date in dates])
    return freq

def round_up(x):
    return x if x % 100 == 0 else x + 100 - x % 100

def count_lenght(results):
    """
    return length of article frequency
    
    :param dict results: mapping hit identifier -> the info about each hit
    
    :rtype: dict
    :return: length_class -> frequency
    """
    contents = [value['_source']['content'].split(' ')
                for value in results.values()]
    
    length_freq = Counter([round_up(len(content))
                      for content in contents])
    
    return length_freq
    
    
    
    
    
    
    
   
