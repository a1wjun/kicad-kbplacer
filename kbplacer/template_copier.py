from pcbnew import *

from .board_modifier import BoardModifier


class TemplateCopier(BoardModifier):
    def __init__(self, logger, board, templatePath, routeTracks):
        super().__init__(logger, board)
        self.template = LoadBoard(templatePath)
        self.boardNetsByName = board.GetNetsByName()
        self.routeTracks = routeTracks

    # Copy positions of elements and tracks from template to board.
    # This method does not copy parts itself - parts to be positioned need to be present in board
    # prior to calling this.
    def run(self):
        footprints = self.template.GetFootprints()

        for footprint in footprints:
            reference = footprint.GetReference()
            destinationFootprint = self.get_footprint(reference)

            layer = footprint.GetLayerName()
            position = footprint.GetPosition()
            orientation = footprint.GetOrientation()

            if layer == "B.Cu" and destinationFootprint.GetLayerName() != "B.Cu":
                destinationFootprint.Flip(destinationFootprint.GetCenter(), False)
            self.set_position(destinationFootprint, position)
            destinationFootprint.SetOrientation(orientation)

        if self.routeTracks:
            tracks = self.template.GetTracks()
            for track in tracks:
                # clone track but remap netinfo because net codes in template might be different.
                # use net names for remmaping (names in template and bourd under modification must match)
                clone = track.Duplicate()
                netName = clone.GetNetname()
                netCode = clone.GetNetCode()
                netInfoInBoard = self.boardNetsByName[netName]
                self.logger.info(
                    f"Cloning track from template: {netName}:{netCode}"
                    f"-> {netInfoInBoard.GetNetname()}:{netInfoInBoard.GetNetCode()}",
                )
                clone.SetNet(netInfoInBoard)
                self.board.Add(clone)
