import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class ChatMessage {
  String text;
  bool outgoing;
  String? senderName;

  ChatMessage({
    required this.text,
    required this.outgoing,
    this.senderName,
  });
}

class Chat extends StatefulWidget {
  final List<ChatMessage> messages;
  final void Function(String message)? onSendMessage;
  final Future<void> Function()? onLoadOlderMessages;

  const Chat({
    super.key,
    required this.messages,
    this.onSendMessage,
    this.onLoadOlderMessages,
  });

  @override
  State<Chat> createState() => _ChatState();
}

class _ChatState extends State<Chat> {
  final TextEditingController _send_controller = TextEditingController();
  late final ScrollController _scroll_controller = ScrollController();
  bool _is_loading_older_messages = false;

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
    _scroll_controller.addListener(() {
      if (_scroll_controller.position.atEdge && _scroll_controller.position.pixels == 0) {
        _onScrollHitTop();
        // BUG: 6:30am now. I wanna detect overscroll at the top. This silly thing doesn't let me grrr so uh I just
        _scroll_controller.jumpTo(1);
      }
    });

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scrollToBottom();
    });
  }

  Future<void> _onScrollHitTop() async {
    if (!_is_loading_older_messages) {
      setState(() {
        _is_loading_older_messages = true;
      });
      await widget.onLoadOlderMessages?.call();
      setState(() {
        _is_loading_older_messages = false;
      });
    }
  }

  void _scrollToBottom() {
    _scroll_controller.jumpTo(_scroll_controller.position.maxScrollExtent);
  }

  void _sendMessage() {
    String trimmed = _send_controller.text.trim();
    if (trimmed.isEmpty) {
      return;
    }
    widget.onSendMessage?.call(trimmed);
    _send_controller.clear();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _scrollToBottom();
      // BUG: yea idfk if we are too far up scrolling once won't do it. It's 6am, I want this to work now lmao
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _scrollToBottom();
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Expanded(
          child: Stack(
            children: [
              if (_is_loading_older_messages)
                Positioned(
                  top: 8,
                  left: 0,
                  right: 0,
                  child: Center(
                    child: SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(),
                    ),
                  ),
                ),
              ListView.builder(
                controller: _scroll_controller,
                padding: const EdgeInsets.all(10),
                itemCount: widget.messages.length,
                itemBuilder: (context, idx) {
                  final message = widget.messages[idx];
                  return Align(
                    alignment: message.outgoing ? Alignment.centerRight : Alignment.centerLeft,
                    child: Container(
                      margin: const EdgeInsets.symmetric(vertical: 5),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: message.outgoing ? Theme.of(context).colorScheme.primaryContainer : Theme.of(context).colorScheme.surfaceContainerHighest,
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Column(
                        crossAxisAlignment: .start,
                        children: [
                          if (message.senderName != null)
                            Text(
                              message.senderName as String,
                              style: TextStyle(
                                color: message.outgoing ? Theme.of(context).colorScheme.onPrimaryContainer : Theme.of(context).colorScheme.onSurface,
                                fontSize: 11,
                              ),
                            ),
                          Text(
                            message.text,
                            style: TextStyle(
                              color: message.outgoing ? Theme.of(context).colorScheme.onPrimaryContainer : Theme.of(context).colorScheme.onSurface,
                              fontSize: 14,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                },
              ),
            ],
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
