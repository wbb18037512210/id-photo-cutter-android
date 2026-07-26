import 'package:flutter_test/flutter_test.dart';

import 'package:id_photo_cutter/main.dart';

void main() {
  testWidgets('首页正常构建并显示标题', (WidgetTester tester) async {
    await tester.pumpWidget(const IdPhotoApp());
    await tester.pumpAndSettle();

    // 首页英雄标题与隐私徽章
    expect(find.text('证件照工作室'), findsWidgets);
    expect(find.text('本地离线 · 数据不出本机'), findsOneWidget);
  });
}
