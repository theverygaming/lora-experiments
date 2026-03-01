import 'dart:convert' as convert;
import 'package:http/http.dart' as http;

enum NodeType { companion, repeater, roomserver, sensor }

class Node {
  NodeType type;
  List<int> pubkey;
  DateTime? lastHeard;
  double? lat;
  double? lon;
  String? name;
  List<int>? outPath;
  int? id;

  Node({
    required this.type,
    required this.pubkey,
    this.lastHeard,
    this.lat,
    this.lon,
    this.name,
    this.outPath,
    this.id,
  });

  factory Node.fromJson(Map<String, dynamic> json) {
    return Node(
      type: _parseNodeType(json['node_type'] as String),
      pubkey: convert.base64Decode(json['pubkey'] as String),
      lastHeard: json['last_heard'] != null ? DateTime.parse(json['last_heard'] as String): null,
      lat: (json['lat'] as num?)?.toDouble(),
      lon: (json['lon'] as num?)?.toDouble(),
      name: json['name'] as String?,
      outPath: (json['out_path'] as List<dynamic>?)?.map((e) => e as int).toList(),
      id: json['id'] as int?,
    );
  }

  static NodeType _parseNodeType(String value) {
    return NodeType.values.firstWhere(
      (e) => e.name == value,
      orElse: () => throw FormatException('Invalid node_type: $value'),
    );
  }
}

Future<List<Node>> fetchNodes() async {
  final response = await http.get(
    Uri.parse('http://127.0.0.1:8000/meshcore/nodes'),
  );

  if (response.statusCode == 200) {
    List<dynamic> decoded = convert.jsonDecode(response.body);
    return decoded.map((json) => Node.fromJson(json)).toList();
  } else {
    throw Exception('Failed to load node');
  }
}
