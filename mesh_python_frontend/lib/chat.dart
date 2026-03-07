import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class ChatMessage {
  String text;
  bool outgoing;

  ChatMessage({
    required this.text,
    required this.outgoing,
  });
}

class Chat extends StatefulWidget {
  const Chat({super.key});

  @override
  State<Chat> createState() => _ChatState();
}

class _ChatState extends State<Chat> {
  List<ChatMessage> messages = [
    ChatMessage(text: "Hii", outgoing: false),
    ChatMessage(text: "Hewwo :3", outgoing: true),
    ChatMessage(text: "woof woof!", outgoing: false),
  ];
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
  }

  void _sendMessage() {
    String trimmed = _send_controller.text.trim();
    if (trimmed.isEmpty) {
      return;
    }
    setState(() {
      messages.add(ChatMessage(text: trimmed, outgoing: true));
    });
    _send_controller.clear();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.all(10),
            itemCount: messages.length,
            itemBuilder: (context, idx) {
              final message = messages[idx];
              return Align(
                alignment: message.outgoing ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  margin: const EdgeInsets.symmetric(vertical: 5),
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: message.outgoing ? Theme.of(context).colorScheme.primaryContainer : Theme.of(context).colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    message.text,
                    style: TextStyle(
                      color: message.outgoing ? Theme.of(context).colorScheme.onPrimaryContainer : Theme.of(context).colorScheme.onSurface,
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
    );
  }
}
