import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_marker_cluster/flutter_map_marker_cluster.dart';
import 'package:latlong2/latlong.dart';
import 'api.dart' as api;
import '../chat.dart';

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int currentPageIndex = 0;
  late Future<List<api.Node>> futureNodes;

  @override
  void initState() {
    super.initState();
    futureNodes = api.fetchNodes();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: [
        Center(
          child: const Text('MeshCore home'),
        ),
        FlutterMap(
          //mapController: MapController(),
          options: MapOptions(
            initialCenter: LatLng(0, 0),
            initialZoom: 2.0,
          ),
          children: [
            TileLayer(
              urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
              userAgentPackageName: 'meow',
            ),
            FutureBuilder<List<api.Node>>(
              future: futureNodes,
              builder: (context, snapshot) {
                List<Marker> markers = [];
                if (snapshot.hasData) {
                  markers = snapshot.data!.where((node) => ((node.lat ?? 0.0) != 0.0 && (node.lon ?? 0.0) != 0.0)).map((node) => (Marker(
                    point: LatLng(node.lat ?? 0.0, node.lon ?? 0.0),
                    width: 150,
                    height: 60,
                    child: GestureDetector(
                      onTap: () {},
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          FlutterLogo(),
                          Text(
                            node.name ?? "unknown name",
                            maxLines: 1,
                            textAlign: TextAlign.center,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(color: Colors.black, fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                    ),
                  ))).toList();
                } else if (snapshot.hasError) {}

                return MarkerClusterLayerWidget(
                  options: MarkerClusterLayerOptions(
                    maxClusterRadius: 45,
                    disableClusteringAtZoom: 18,
                    size: const Size(40, 40),
                    alignment: Alignment.center,
                    padding: const EdgeInsets.all(50),
                    maxZoom: 15,        
                    markers: markers,
                    builder: (context, markers) {
                      return Container(
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(20),
                          color: (
                            // >= 100 -> red
                            // >= 10 -> yellow
                            // < 10 -> green
                            markers.length < 100 ? (markers.length < 10 ? Colors.green : Colors.yellow) : Colors.red
                          ),
                        ),
                        child: Center(
                          child: Text(
                            markers.length.toString(),
                            style: const TextStyle(color: Colors.black),
                          ),
                        ),
                      );
                    },
                  ),
                );
              }
            ),
          ],
        ),
        Chat(),
      ][currentPageIndex],
      bottomNavigationBar: NavigationBar(
        onDestinationSelected: (int index) {
          setState(() {
            currentPageIndex = index;
          });
        },
        selectedIndex: currentPageIndex,
        destinations: const <Widget>[
          NavigationDestination(
            selectedIcon: Icon(Icons.home),
            icon: Icon(Icons.home_outlined),
            label: 'Home',
          ),
          NavigationDestination(
            icon: Icon(Icons.map),
            label: 'Node Map',
          ),
          NavigationDestination(
            icon: Icon(Icons.chat),
            label: 'Chats',
          ),
        ],
      ),
    );
  }
}
