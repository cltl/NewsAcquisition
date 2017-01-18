import requests
import operator
import os
import json
from SPARQLWrapper import SPARQLWrapper, JSON
import datetime
from collections import Counter

questions_file = "questions.tsv"
corpus_dir="corpus/"

sparql_endpoint="http://sparql.fii800.lod.labs.vu.nl/sparql"
graph_uri="http://longtailcorpus.org"

def get_me_a_query(labels="'earthquake', 'quake', 'temblor', 'seism', 'tremor'", t=True, l=True, p=False, strictLocations=True, pagerank=True, pr_limit=500.0):
    query = get_sparql_top() + get_sparql_middle(labels, t, l, p, strictLocations, pagerank, pr_limit) + get_sparql_bottom()
    return query

def get_sparql_top():
    return """
	PREFIX sem: <http://semanticweb.cs.vu.nl/2009/11/sem/>
	PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
	PREFIX dbpedia: <http://dbpedia.org/resource/>
	PREFIX owltime: <http://www.w3.org/TR/owl-time#>
	PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
	PREFIX dbo: <http://dbpedia.org/ontology/>
	PREFIX vrank: <http://purl.org/voc/vrank#>
	PREFIX dbc: <http://dbpedia.org/resource/Category:>
	PREFIX dc: <http://purl.org/dc/elements/1.1/>
	PREFIX dct: <http://purl.org/dc/terms/>
	SELECT ?event ?location ?time ?participant WHERE {
    """

def get_sparql_bottom():
    return """
	}
    """

def get_sparql_middle(labels="'earthquake', 'quake', 'temblor', 'seism', 'tremor'", t=True, l=True, p=False, strictLoc=True, pagerank=True, pr_limit=500.0): # t->time, l->location, p->participants

    timeString="\n\t\t?event sem:hasTime ?tmx . ?tmx owltime:inDateTime ?time . " if t else ""
    locationString="\n\t\t?event sem:hasPlace ?location . " if l else ""
    locationConstraint="""
		?location a ?x . ?x rdfs:subClassOf* dbo:Place . 
		FILTER NOT EXISTS { ?location dct:subject dbc:States_of_the_United_States } .
		FILTER (!REGEX(STR(?x), 'http://dbpedia.org/ontology/Country')) .
		FILTER NOT EXISTS { ?x rdfs:subClassOf* dbo:Country  } . """ if strictLoc else ""
    participantString="\n\t\t?event sem:hasActor ?participant . " if p else ""
    pageRankString="""
		?location vrank:hasRank/vrank:rankValue ?pagerank .
		FILTER (xsd:float(?pagerank)<=%f) .
    """ % pr_limit if pagerank else ""

    return """
		?event a sem:Event .
		{ ?event rdfs:label ?label .
		FILTER (?label IN (%s)) } 
		UNION
		{ ?event sem:hasActor ?nonentity .
		?nonentity skos:relatedMatch dbpedia:Earthquake } 
		UNION
  		{ ?event sem:hasActor ?nonentity .
		?nonentity skos:relatedMatch ?earthquakeX .
  		?earthquakeX a dbo:Earthquake } .  %s %s %s %s %s
    """ % (labels, timeString, locationString, locationConstraint, participantString, pageRankString)


def intersection(b1, b2):
    if not len(b1) or not len(b2):
        return 0.0
    shared=[val for val in b1 if val in b2]
    return len(shared)/min(len(set(b1)),len(set(b2)))
    
def coreferential(t1, t2, p1, p2, l1, l2, days, p_overlap, l_overlap):
    return all([time_diff(t1,t2)<=days, intersection(p1,p2)>=p_overlap, intersection(l1,l2)>=l_overlap])

def to_dbpedia(locs):
    uris=set()
    for l in locs:
        uris.add("'http://dbpedia.org/resource/%s'" % l)
    return ",".join(uris)


def get_news_from_fun_locations(ids):
    query = get_sparql_top() + get_sparql_middle(ids) + get_sparql_bottom()
    print(query)
    res=get_sparql_results(query)
    return res

def time_diff(t1, t2):
    ta=datetime.datetime.strptime(t1, '%Y-%m-%dT%H:%M:%S')
    tb=datetime.datetime.strptime(t2, '%Y-%m-%dT%H:%M:%S')
    return abs((ta-tb).days)

def get_sparql_results(query):

    sparql = SPARQLWrapper(sparql_endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    sparql.method = 'POST'
    results = sparql.query().convert()
    return results["results"]["bindings"]

def obtain_specific_identifiers(path_signalmedia_json, identifiers):
    """
    create generator of json objects (representing signalmedia articles)
    
    :param str path_signalmedia_json: path to all signalmedia article in jsonl
    (originally called signalmedia-1m.jsonl
    :param set identifiers: the json objects for the identifiers
    are returned
    
    :rtype: dict
    :return: identifier -> json object
    """
    results = dict()
    with open(path_signalmedia_json) as infile:
        for counter, line in enumerate(infile, 1):
            article = json.loads(line)
            if article['id'] in identifiers:
                results[article['id']] = article
    return results

def insert_qa(question, answer, query):
	w=open(questions_file, 'a')
	w.write('%s\t%s\t%s\n' % (question, answer, query))
	w.close()

def store_all_current_documents(q, results):
	q=q.replace(' ', '_')
	mydir=corpus_dir + q
	os.mkdir(mydir)
	for res in results.values():
		src=res['_source']
		title=src['title']
		content=src['content']
		id=src['id']
		with open(mydir + '/' + id + '.txt', 'w') as w:
			w.write('%s\n%s' % (title, content))

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
    
    
    
"""
def get_sparql_top():
    return '''PREFIX dct: <http://purl.org/dc/terms/>
PREFIX nif: <http://persistence.uni-leipzig.org/nlp2rdf/ontologies/nif-core#>
PREFIX gaf: <http://groundedannotationframework.org/gaf#>
SELECT ?n1 ?src (group_concat(?location;separator="|") as ?locations) ?dct WHERE {
  GRAPH <http://longtailcorpus.org> {
    '''

def get_sparql_bottom():
    return " } } ORDER BY ?dct"

def get_sparql_middle(ids):    

    return '''?n1 a nif:Context ;
    dct:source ?src .
    FILTER (?src IN (''' + ids + ''')) .
    ?mention nif:referenceContext ?n1 .
    ?n1 dct:created ?dct ;
    dct:publisher ?pub .
    ?mention nif:referenceContext ?n1 ;
     gaf:denotes ?locentity . ?locentity a <http://cltl.nl/type/GPE> . ?mention nif:anchorOf ?location .
    '''
"""


    
    
    
   
