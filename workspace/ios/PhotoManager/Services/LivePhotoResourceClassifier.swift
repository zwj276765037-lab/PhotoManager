import Photos

struct LivePhotoResources {
    let photo: PHAssetResource
    let pairedVideo: PHAssetResource
}

enum LivePhotoResourceClassifier {
    static func classify(_ resources: [PHAssetResource]) throws -> LivePhotoResources {
        let photo = resources.first(where: { $0.type == .fullSizePhoto })
            ?? resources.first(where: { $0.type == .photo })
        let pairedVideo = resources.first(where: { $0.type == .fullSizePairedVideo })
            ?? resources.first(where: { $0.type == .pairedVideo })

        guard let photo else {
            throw LivePhotoPipelineError.missingPhotoResource
        }
        guard let pairedVideo else {
            throw LivePhotoPipelineError.missingPairedVideoResource
        }
        return LivePhotoResources(photo: photo, pairedVideo: pairedVideo)
    }
}

