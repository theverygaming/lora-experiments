import 'package:flutter/material.dart';
import 'meshcore/main.dart' as mc;

void main() {
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'silly',
      theme: ThemeData(
        brightness: Brightness.light,
        colorScheme: .fromSeed(seedColor: Colors.deepPurple, brightness: Brightness.light),
      ),
      darkTheme: ThemeData(
        brightness: Brightness.dark,
        colorScheme: .fromSeed(seedColor: Colors.deepPurple, brightness: Brightness.dark),
      ),
      themeMode: ThemeMode.system,
      home: const MyHomePage(title: 'silly'),
    );
  }
}

class MyHomePage extends StatefulWidget {
  const MyHomePage({super.key, required this.title});

  final String title;

  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  int currentAppModeIndex = 1;

  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: Theme.of(context).colorScheme.inversePrimary,
        title: Text(widget.title),
        actions: [IconButton(
          icon: const Icon(Icons.swap_horiz),
          onPressed: () => showModalBottomSheet(
            context: context,
            builder: (_) => Column(
              mainAxisSize: MainAxisSize.min,
              children: ["experiment", "MeshCore"].asMap().entries.map((value) {
                return ListTile(
                  title: Text(value.value),
                  selected: false,
                  onTap: () {
                    setState(() {
                      currentAppModeIndex = value.key;
                    });
                    Navigator.pop(context); // closes modal
                  },
                );
              }).toList(),
            ),
          ),
        )],
      ),
      body: [
        Center(
          child: const Text('Experiment'),
        ),
        mc.MyHomePage(),
      ][currentAppModeIndex],
    );
  }
}
