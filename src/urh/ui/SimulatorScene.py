from PyQt5.QtWidgets import QGraphicsScene, QGraphicsLineItem, QGraphicsTextItem, QGraphicsItemGroup, QGraphicsSceneDragDropEvent, QGraphicsItem, QMenu, QAction
from PyQt5.QtGui import QPen, QDragEnterEvent, QDropEvent, QPolygonF, QColor, QFont, QFontDatabase, QTransform
from PyQt5.QtCore import Qt, QRectF, QSizeF, QPointF, QSizeF
import math
from enum import Enum

from urh import constants
from urh.signalprocessing.Message import Message

class ConditionType(Enum):
    IF = "if ..."
    ELSE_IF = "else if ..."
    ELSE = "else"

class RuleItem(QGraphicsItem):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.conditions = []
        self.conditions.append(RuleConditionItem(ConditionType.IF, self))

    def has_else_condition(self):
        return len([cond for cond in self.conditions if cond.type is ConditionType.ELSE]) == 1

    def get_all_messages(self):
        messages = []

        for cond in self.conditions:
            messages.extend([item for item in cond.items if type(item) is MessageItem])

        return messages

    def delete_selected_items(self):
        for condition in self.conditions:
            for item in [item for item in condition.items if item.isSelected()]:
                condition.items.remove(item)
                self.scene().removeItem(item)
            
    def update(self, y_pos):
        if_cond = [cond for cond in self.conditions if cond.type is ConditionType.IF][0]

        if_cond.update(y_pos)
        y_pos += math.floor(if_cond.boundingRect().height())

        for cond in [cond for cond in self.conditions if cond.type is ConditionType.ELSE_IF]:
            cond.update(y_pos)
            y_pos += math.floor(cond.boundingRect().height())

        else_cond = [cond for cond in self.conditions if cond.type is ConditionType.ELSE]

        if len(else_cond) == 1:
            else_cond[0].update(y_pos)

        super().update()

    def boundingRect(self):
        return self.childrenBoundingRect()

    def paint(self, painter, option, widget):
        pass

class RuleTextItem(QGraphicsTextItem):
    def __init__(self, text, color, parent=None):
        super().__init__(parent)
        self.color = color
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(10)
        font.setWeight(QFont.DemiBold)
        self.setFont(font)
        self.setPlainText(text)

    def paint(self, painter, option, widget):
        #painter.setBrush(self.color)
        painter.setPen(QPen(QColor(Qt.transparent), Qt.FlatCap))
        painter.drawRect(self.boundingRect())
        super().paint(painter, option, widget)

class RuleConditionItem(QGraphicsItem):
    def __init__(self, type, parent):
        super().__init__(parent)
        self.type = type
        self.text = RuleTextItem(type.value, QColor.fromRgb(139,148,148), self)        
        self.items = []
        self.rect = QRectF()

    def update(self, y_pos):
        if not self.scene() or len(self.scene().participants) < 2:
            return

        x = self.scene().participants[0].line.line().x1()
        tmp_y = y_pos

        width = self.scene().participants[-1].line.line().x1() - x
        self.prepareGeometryChange()
        self.text.setPos(-20, tmp_y)
        tmp_y += math.floor(self.text.boundingRect().height()) + 1

        for item in self.items:
            item.update(tmp_y)
            tmp_y += math.floor(item.boundingRect().height()) + 1

        self.rect.setRect(x - 20, y_pos, width + 40, tmp_y - y_pos)
        super().update()

    def boundingRect(self):
        return self.rect

    def paint(self, painter, option, widget):
        #painter.setBrush(QColor.fromRgb(61,67,67,125))
        painter.drawRect(self.boundingRect())

    def contextMenuEvent(self, event):
        menu = QMenu()

        addMessageAction = QAction("Add empty message")
        addElseIfCondAction = QAction("Add else if block")
        addElseCondAction = QAction("Add else block")

        menu.addAction(addMessageAction)
        menu.addAction(addElseIfCondAction)

        if not self.parentItem().has_else_condition():
            menu.addAction(addElseCondAction)

        action = menu.exec_(event.screenPos())

        if action == addMessageAction:
            source = self.scene().not_assigned_part
            destination = self.scene().broadcast_part
            simulator_message = MessageItem(source, destination, self)
            simulator_message.add_label(LabelItem("preamble", constants.LABEL_COLORS[0]))
            simulator_message.add_label(LabelItem("synchronization", constants.LABEL_COLORS[1]))
            self.items.append(simulator_message)
        elif action == addElseIfCondAction:
            self.parentItem().conditions.append(RuleConditionItem(ConditionType.ELSE_IF, self.parentItem()))
        elif action == addElseCondAction:
            self.parentItem().conditions.append(RuleConditionItem(ConditionType.ELSE, self.parentItem()))

        self.scene().update_view()

class LabelItem(QGraphicsTextItem):
    def __init__(self, text, color, parent=None):
        super().__init__(parent)
        self.color = color
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(8)
        self.setFont(font)
        self.setPlainText(text)

    def paint(self, painter, option, widget):
        painter.setBrush(self.color)
        painter.drawRect(self.boundingRect())
        super().paint(painter, option, widget)

class ParticipantItem(QGraphicsItem):
    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.text = QGraphicsTextItem(name, self)
        self.line = QGraphicsLineItem(self)
        self.line.setPen(QPen(Qt.darkGray, 1, Qt.DashLine, Qt.RoundCap, Qt.RoundJoin))

    def update(self, x_pos = -1, y_pos = -1):
        if not self.scene():
            return

        if x_pos == -1:
            x_pos = self.line.line().x1()

        if y_pos == -1:
            y_pos = self.line.line().y2()

        self.prepareGeometryChange()
        self.text.setPos(x_pos - (self.text.boundingRect().width() / 2), 0)
        self.line.setLine(x_pos, 30, x_pos, y_pos)
        super().update()

    def boundingRect(self):
        return self.childrenBoundingRect()

    def paint(self, painter, option, widget):
        pass

class MessageItem(QGraphicsItem):
    def __init__(self, source, destination, parent=None):
        super().__init__(parent)
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.arrow = MessageArrowItem(self)
        self.source = source
        self.destination = destination
        self.labels = []
        self.setAcceptHoverEvents(True)
        self.hover_active = False

    def hoverEnterEvent(self, event):
        self.hover_active = True
        super().update()

    def hoverLeaveEvent(self, event):
        self.hover_active = False
        super().update()

    def labels_width(self):
        width = sum([lbl.boundingRect().width() for lbl in self.labels])
        width += 5 * (len(self.labels) - 1)
        return width

    def add_label(self, label: LabelItem):
        label.setParentItem(self)
        self.labels.append(label)

    def update(self, y_pos):
        arrow_width = abs(self.source.line.line().x1() - self.destination.line.line().x1())

        start_x = min(self.source.line.line().x1(), self.destination.line.line().x1())
        start_x += (arrow_width - self.labels_width()) / 2

        self.prepareGeometryChange()

        for label in self.labels:
            label.setPos(start_x, y_pos)
            start_x += label.boundingRect().width() + 5

        if len(self.labels) > 0:
            y_pos += self.labels[0].boundingRect().height() + 5

        self.arrow.setLine(self.source.line.line().x1(), y_pos, self.destination.line.line().x1(), y_pos)
        
        super().update()

    def boundingRect(self):
        return self.childrenBoundingRect()

    def paint(self, painter, option, widget):
        if self.hover_active or self.isSelected():
            rect = self.boundingRect()
            painter.setOpacity(constants.SELECTION_OPACITY)
            painter.setBrush(constants.SELECTION_COLOR)
            painter.setPen(QPen(QColor(Qt.transparent), Qt.FlatCap))
            painter.drawRect(self.boundingRect())

class MessageArrowItem(QGraphicsLineItem):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPen(QPen(Qt.black, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

    def boundingRect(self):
        extra = (self.pen().width() + 20) / 2.0

#        return QRectF(self.line().p1(), QSizeF(self.line().p2().x() - self.line().p1().x(),
#                    self.line().p2().y() - self.line().p1().y())).normalized().adjusted(-extra, -extra, extra, extra)

        return super().boundingRect().adjusted(0, -7, 0, 7)

    def paint(self, painter, option, widget):
        if self.line().length() == 0:
            return

        myPen = self.pen()
        myPen.setColor(Qt.black)
        arrowSize = 10.0
        painter.setPen(myPen)
        painter.setBrush(Qt.black)

        angle = math.acos(self.line().dx() / self.line().length())

        if self.line().dy() >= 0:
            angle = (math.pi * 2) - angle

        arrowP1 = self.line().p2() - QPointF(math.sin(angle + math.pi / 2.5) * arrowSize,
                    math.cos(angle + math.pi / 2.5) * arrowSize)

        arrowP2 = self.line().p2() - QPointF(math.sin(angle + math.pi - math.pi / 2.5) * arrowSize,
                    math.cos(angle + math.pi - math.pi / 2.5) * arrowSize)

        arrowHead = QPolygonF()
        arrowHead.append(self.line().p2())
        arrowHead.append(arrowP1)
        arrowHead.append(arrowP2)

        painter.drawLine(self.line())
        painter.drawPolygon(arrowHead)

class SimulatorScene(QGraphicsScene):
    def __init__(self, parent=None, controller=None):
        super().__init__(parent)
        self.controller = controller
        self.tree_root_item = None

        self.participants_dict = {}
        self.participants = []

        self.not_assigned_part = ParticipantItem("?")
        self.participants.append(self.not_assigned_part)
        self.addItem(self.not_assigned_part)

        self.broadcast_part = ParticipantItem("Broadcast")
        self.participants.append(self.broadcast_part)
        self.addItem(self.broadcast_part)

        self.items = []
        self.update_view()

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton:
            event.accept()
            return

        super().mousePressEvent(event)

    def contextMenuEvent(self, event):
        if self.itemAt(event.scenePos(), QTransform()) is not None:
            super().contextMenuEvent(event)
            return

        menu = QMenu()

        delAction = QAction("Delete selected messages")
        addRuleAction = QAction("Add rule")

        if len(self.selectedItems()) > 0:
            menu.addAction(delAction)

        menu.addAction(addRuleAction)

        action = menu.exec_(event.screenPos())

        if action == delAction:
           self.delete_selected_items()
        elif action == addRuleAction:
            rule = RuleItem()
            self.items.append(rule)
            self.addItem(rule)
            self.update_view()

    def delete_selected_items(self):
        for item in self.items[:]:
            if type(item) == MessageItem and item.isSelected():
                self.items.remove(item)
                self.removeItem(item)
            elif type(item) == RuleItem:
                item.delete_selected_items()

        self.update_view()

    def update_view(self):
        self.update_participants(self.controller.project_manager.participants)

        for item in self.items[:]:
            if type(item) is MessageItem and (item.source not in self.participants or item.destination not in self.participants):
                self.items.remove(item)
                self.removeItem(item)

        self.arrange_participants()
        self.arrange_items()

        # resize scrollbar
        rect = self.itemsBoundingRect()

        if rect is None:
            self.setSceneRect(QRectF(0, 0, 1, 1))
        else:
            self.setSceneRect(rect)

    def update_participants(self, participants):
        for key in list(self.participants_dict.keys()):
            if key not in participants:
                self.removeItem(self.participants_dict[key])
                self.participants.remove(self.participants_dict[key])
                del self.participants_dict[key]

        for participant in participants:
            if participant in self.participants_dict:
                participant_item = self.participants_dict[participant]
                participant_item.text.setPlainText(participant.shortname)
            else:
                participant_item = ParticipantItem(participant.shortname)
                self.addItem(participant_item)
                self.participants_dict[participant] = participant_item
                self.participants.append(participant_item)

    def get_all_messages(self):
        messages = []

        for item in self.items:
            if type(item) is MessageItem:
                messages.append(item)
            elif type(item) is RuleItem:
                messages.extend(item.get_all_messages())

        return messages

    def arrange_participants(self):
        if len(self.participants) < 1:
            return

        self.participants[0].update(x_pos = 0)

        for i in range(1, len(self.participants)):
            curr_participant = self.participants[i]
            participants_left = self.participants[:i]

            items = [msg for msg in self.get_all_messages()
                    if ((msg.source == curr_participant and msg.destination in participants_left)
                    or (msg.source in participants_left and msg.destination == curr_participant))]

            x_max = self.participants[i - 1].line.line().x1() + 50

            for msg in items:
                x = msg.labels_width() +  30
                x += msg.source.line.line().x1() if msg.source != curr_participant else msg.destination.line.line().x1()

                if x > x_max:
                    x_max = x

            curr_participant.update(x_pos = x_max)

    def arrange_items(self):
        y_pos = 30

        for item in self.items:
            item.update(y_pos)
            y_pos += math.floor(item.boundingRect().height()) + 5

        for participant in self.participants:
            participant.update(y_pos = max(y_pos, 50))

    def dragEnterEvent(self, event: QGraphicsSceneDragDropEvent):
        event.setAccepted(True)

    def dragMoveEvent(self, event: QGraphicsSceneDragDropEvent):
        pass

    def dropEvent(self, event: QDropEvent):
        indexes = list(event.mimeData().text().split("/")[:-1])

        group_nodes = []
        file_nodes = []
        for index in indexes:
            try:
                row, column, parent = map(int, index.split(","))
                if parent == -1:
                    parent = self.tree_root_item
                else:
                    parent = self.tree_root_item.child(parent)
                node = parent.child(row)
                if node.is_group:
                    group_nodes.append(node)
                else:
                    file_nodes.append(node)
            except ValueError:
                continue

        # Which Nodes to add?
        nodes_to_add = []
        """:type: list of ProtocolTreeItem """
        for group_node in group_nodes:
            nodes_to_add.extend(group_node.children)
        nodes_to_add.extend([file_node for file_node in file_nodes if file_node not in nodes_to_add])
        protocols_to_add = [node.protocol for node in nodes_to_add]


        self.add_protocols(protocols_to_add)

        self.update_view()

        super().dropEvent(event)

    def add_protocols(self, protocols_to_add: list):
        for protocol in protocols_to_add:
            for message in protocol.messages:
                source, destination = self.__detect_source_destination(message)
                simulator_message = MessageItem(source, destination)
                for label in message.message_type:
                    simulator_message.add_label(LabelItem(label.name, constants.LABEL_COLORS[label.color_index]))
                self.items.append(simulator_message)
                self.addItem(simulator_message)

    def __detect_source_destination(self, message: Message):
        # TODO: use SRC_ADDRESS and DST_ADDRESS labels
        participants = self.controller.project_manager.participants

        source = None
        destination = None

        if len(participants) == 0:
            source = self.not_assigned_part
            destination = self.broadcast_part
        elif len(participants) == 1:
            source = self.participants_dict[participants[0]]
            destination = self.broadcast_part
        else:
            if message.participant:
                source = self.participants_dict[message.participant]
                destination = self.participants_dict[participants[0]] if message.participant == participants[1] else self.participants_dict[participants[1]]
            else:
                source = self.participants_dict[participants[0]]
                destination = self.participants_dict[participants[1]]

        return (source, destination)