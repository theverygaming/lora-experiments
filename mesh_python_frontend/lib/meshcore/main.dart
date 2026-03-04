import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_map_marker_cluster/flutter_map_marker_cluster.dart';
import 'package:flutter/services.dart';
import 'package:latlong2/latlong.dart';
import 'api.dart' as api;

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key});

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int currentPageIndex = 0;
  late Future<List<api.Node>> futureNodes;
  List<List<dynamic>> messages = [["Hii", false], ["Hewwo :3", true], ["woof woof!", false]];
  final TextEditingController _send_controller = TextEditingController();

  // https://stackoverflow.com/a/69359022
  late final _send_focusNode = FocusNode(
    onKeyEvent: (FocusNode node, KeyEvent evt) {
      if (!HardwareKeyboard.instance.isShiftPressed && evt.logicalKey.keyLabel == 'Enter') {
        if (evt is KeyDownEvent) {
          _sendMessage();
        }
        return KeyEventResult.handled;
      } else {
        return KeyEventResult.ignored;
      }
    },
  );


  @override
  void initState() {
    super.initState();
    futureNodes = api.fetchNodes();
  }

  void _sendMessage() {
    String trimmed = _send_controller.text.trim();
    if (trimmed.isEmpty) {
      return;
    }
    setState(() {
      messages.add([trimmed, true]);
    });
    _send_controller.clear();
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
        Column(
          children: [
            Expanded(
              child: ListView.builder(
                padding: const EdgeInsets.all(10),
                itemCount: messages.length,
                itemBuilder: (context, idx) {
                  final message = messages[idx];
                  return Align(
                    alignment: (message[1] as bool) ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.symmetric(vertical: 5),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: (message[1] as bool) ? Theme.of(context).colorScheme.primaryContainer : Theme.of(context).colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(
                        (message[0] as String),
                        style: TextStyle(
                          color: (message[1] as bool) ? Theme.of(context).colorScheme.onPrimaryContainer : Theme.of(context).colorScheme.onSurface,
                          fontSize: 14,
                        ),
                      ),
                    ),
                  );
                },
              ),
            ),
            SafeArea(
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _send_controller,
                      autofocus: true,
                      focusNode: _send_focusNode,
                      decoration: InputDecoration(
                        hintText: "bark here...",
                        border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 10),
                      ),
                      maxLines: null, // allows newline
                      textInputAction: TextInputAction.newline, // apparently shows the return key on mobile keyboards
                    ),
                  ),
                  IconButton(
                    icon: Icon(Icons.send, color: Theme.of(context).colorScheme.primary),
                    onPressed: _sendMessage,
                  ),
                ],
              ),
            ),
          ],
        ),
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
