import argparse
import json
import re
from collections import Counter
from urllib.parse import quote_plus

import requests
import xmltodict

__author__    = "@Wietze"
__copyright__ = "(c) 2016-2024"
__licence__   = "GPLv3"

API_KEY_GUARDIAN = 'test' # Or put your own API key here
API_GUARDIAN = "http://content.guardianapis.com/search?q={{keyword}}&show-tags=keyword&api-key={api_key}&page-size=50&order-by=newest".format(api_key=API_KEY_GUARDIAN)
API_PARLIAMENT = "http://data.parliament.uk/membersdataplatform/services/mnis/members/query/House=Commons|IsEligible=true/"
# When Parliament is not in session, replace `IsEligible=true` with the following in the above query condition: `MemberShip=All|LeftSince=yyyy-mm-dd`

PARTY_COLOURS = {"Labour":[220./255, 36./255, 31./255, 1], "Conservative":[0, 135/255, 220/255, 1], "Social Democratic & Labour Party": [0, 135/255, 220/255, 1], "Scottish National Party":[1, 1, 0, 1], "Liberal Democrat":[253/255, 187/255, 48/255, 1], "UK Independence Party":[75/255, 0/255, 199/255, 1], "Green Party": [105/255, 245/255, 0, 1], "Labour (Co-op)": [220./255, 36./255, 31./255, 1], "Democratic Unionist Party": [204/255, 51/255, 0, 1], "Sinn Fein":[0, 102/255, 0, 1], "Ulster Unionist Party": [153/255, 153/255, 1, 1]}
normalise_name = lambda x: re.sub('^(Sir |Dame |Mr |Ms |Mrs |Dr )', '', x).strip()

def get_mp_data():
    print("Querying for MPs...")
    mps = xmltodict.parse(requests.get(API_PARLIAMENT).text)

    # Create common structure
    members = {normalise_name(member['DisplayAs']): {"party": member['Party']['#text'], "id":id, "mentioned_with":[], 'degree':0} for id, member in enumerate(mps["Members"]["Member"])}

    session = requests.Session()
    for i, member in enumerate(members.keys(), start=1):
        print("Querying the Guardian... [{}/{}]".format(i, len(members)), end="\r")
        url = API_GUARDIAN.format(keyword=quote_plus(f'"{member}"'))
        guardian_result = session.get(url)
        assert guardian_result.status_code == 200
        guardian_data = guardian_result.json()
        if not guardian_data["response"]["results"]: continue
        tags = []
        for result in guardian_data["response"]["results"]:
            tags.extend([tag['webTitle'] for tag in result["tags"]])
        tagcount = Counter(tags)

        for compare_member in members:
            if compare_member == member or tagcount[compare_member] == 0: continue
            members[member]["mentioned_with"].append({'name': compare_member, 'count': tagcount[compare_member]})
            members[member]["degree"] += 1
            members[compare_member]["degree"] += 1

    print("Querying The Guardian...")
    return members

def generate_d3_json(members, output_file):
    # Write to file
    print("Writing to file...")
    for (name, member) in members.items():
        member['name'] = name

    with open(output_file, 'w') as outfile:
        json.dump(list(members.values()), outfile)

def generate_graph_tool(members, output_file):
    from graph_tool.all import Graph, NestedBlockState, draw_hierarchy
    print("Drawing graph...")

    # Renumber member IDs to be ascending, without gaps (necessary because graph_tool doesn't handle series with missing number well)
    id_map = {member['id']:i for i, (_, member) in enumerate(members.items())}

    # Generate edges in the right format
    edges = [(id_map[member['id']], id_map[members[compare_member['name']]['id']], compare_member['count']) for name, member in members.items() for compare_member in member['mentioned_with']]
    member_dict = sorted(members.values(), key=lambda x: id_map[x['id']])

    # Set up graph
    g = Graph(directed=True)
    g.add_vertex(len(members))
    g.add_edge_list(edges)

    # Filter (only showing those MPs that are mentioned)
    filter =  g.new_vertex_property("bool")
    filter.a = [member['degree'] > 0 for member in member_dict]

    # Names
    names = g.new_vertex_property("string")
    for name, member in members.items():
        names[g.vertex(id_map[member['id']])] = name

    # Weights (= number of articles of two MPs)
    weights = g.new_edge_property("float")
    weights.a = [float(weight) for (_, _, weight) in edges]

    # Colour (= party colour)
    colour = g.new_vertex_property("vector<float>")
    for member in members.values():
        colour[g.vertex(id_map[member['id']])] = PARTY_COLOURS[member['party']] if member['party'] in PARTY_COLOURS else [0, 0, 0, 1]

    g.set_vertex_filter(filter)
    parties = {party_name:id for (id, party_name) in enumerate(set([member['party'] for member in members.values()]))}

    # Creating clustering based on party
    level0 = g.new_vertex_property('int')
    level0.a = [parties[member['party']] for member in member_dict]
    level1 = g.new_vertex_property('int')
    level1.a = [0] * len(member_dict)
    state = NestedBlockState(g, [level0, level1])

    print("Writing to file..." if output_file else "Displaying graph...")
    # Draw the graph
    draw_hierarchy(state, output=output_file, vertex_text=names, edge_pen_width=weights, vertex_fill_color=colour, vertex_size=10, vertex_text_position="centered", vertex_font_size=12, output_size=(1920, 1080), highlight_color=[0, 0, 0, 1], hide=5)

def load_data(input_file):
    with open(input_file) as json_file:
        json_data = json.load(json_file)
    return {member['name']:member for member in json_data}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create a connection graph for MPs mentioned in articles of the Guardian.')
    parser.add_argument('--output', type=str,
                       help='Specify output file (supported formats: JSON, PDF, SVG, EPS) or leave empty for interactive window.')
    parser.add_argument('--input', type=str,
                       help='Specify output file (JSON).')
    args = parser.parse_args()

    # Load data either from file or by downloading data from the APIs
    data = load_data(args.input) if args.input else get_mp_data()

    if args.output and args.output.endswith('.json'):
        generate_d3_json(members=data, output_file=args.output)
    else:
        generate_graph_tool(members=data, output_file=args.output)
