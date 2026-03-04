# nix-shell -p python311Packages.geopy -p python311Packages.shapely --pure
import json
import geopy.distance
import shapely

TRACE_PATH = [..]
START_COORDS = (.., ..)

CONSTRAINT = shapely.geometry.Polygon([
    (.., ..)
])

if __name__ == "__main__":
    # https://api.letsmesh.net/api/nodes?updated_since=2026-02-20T09%3A23%3A53.553Z
    with open("api_nodes_fair.json", "r", encoding="utf-8") as f:
        nodes = json.loads(f.read())

    print(nodes["nodes"][0])

    nodes_by_prefix = {}
    for node in nodes["nodes"]:
        # only repeaters and room servers (those may be repeaters apparently)
        if node["device_role"] not in [2, 3]:
            continue
        # only nodes with a location
        if node["location"] is None:
            continue
        # only nodes within constraints
        if not CONSTRAINT.contains(shapely.geometry.Point(node["location"]["latitude"], node["location"]["longitude"])):
            continue
        prefix = int(node["public_key"][:2], base=16)
        if prefix not in nodes_by_prefix:
            nodes_by_prefix[prefix] = []
        nodes_by_prefix[prefix].append(node)
    
    print(f"dealing with {sum(len(x) for x in nodes_by_prefix.values())} nodes")

    def find_close(coords, prefix):
        # this is... far from ideal! But it might just work for some cases...
        options_with_distance = [
            (node, dist) for node in nodes_by_prefix[prefix]
            if (dist := geopy.distance.geodesic(coords, (node["location"]["latitude"], node["location"]["longitude"])).kilometers) < 100
        ]

        # sort by distance, lowest first
        options_with_distance = list(sorted(options_with_distance, key=lambda x: x[1]))

        return options_with_distance
    
    def descend_options(coords, path):
        if len(path) == 0:
            return [[]]
        options_with_distance = find_close(coords, path[0])
        paths_possible = []
        for i, option in enumerate(options_with_distance):
            closest_node, closest_dist = option
            subpaths = descend_options(
                (closest_node["location"]["latitude"], closest_node["location"]["longitude"]),
                path[1:],
            )
            for p in subpaths:
                paths_possible.append([(closest_dist)] + p)
            #if i == 3:
            #    break
        return paths_possible
    
    paths_possible = descend_options(START_COORDS, TRACE_PATH)

    # print(paths_possible)
    print(len(paths_possible))

    #current_coords = START_COORDS
    # for prefix in TRACE_PATH:
    #     print(f"analyzing hop: {hex(prefix)}:")
    #     options_with_distance = find_close(current_coords, prefix)
    #     closest_node, closest_dist = options_with_distance[0]
    #     print(f'closest node: "{closest_node["name"]}" ({closest_dist:.3f}km) - https://analyzer.letsmesh.net/nodes/repeaters?public_key={closest_node["public_key"]}')
    #     current_coords = (closest_node["location"]["latitude"], closest_node["location"]["longitude"])
    #     print("---")
