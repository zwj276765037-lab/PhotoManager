import Photos
import PhotosUI
import SwiftUI

struct LivePhotoPlayerView: UIViewRepresentable {
    let livePhoto: PHLivePhoto

    func makeUIView(context: Context) -> PHLivePhotoView {
        let view = PHLivePhotoView()
        view.contentMode = .scaleAspectFit
        return view
    }

    func updateUIView(_ uiView: PHLivePhotoView, context: Context) {
        uiView.stopPlayback()
        uiView.livePhoto = livePhoto
        uiView.startPlayback(with: .full)
    }
}

