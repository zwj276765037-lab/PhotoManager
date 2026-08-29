import Photos

final class LivePhotoExportService {
    func saveAsNewLivePhoto(_ imported: ImportedLivePhoto) async throws -> String {
        let authorization = await PHPhotoLibrary.requestAuthorization(for: .addOnly)
        guard authorization == .authorized || authorization == .limited else {
            throw LivePhotoPipelineError.addPermissionDenied
        }

        var createdLocalIdentifier: String?
        let _: Void = try await withCheckedThrowingContinuation { continuation in
            PHPhotoLibrary.shared().performChanges {
                let request = PHAssetCreationRequest.forAsset()

                let photoOptions = PHAssetResourceCreationOptions()
                photoOptions.shouldMoveFile = false
                photoOptions.originalFilename = imported.photoOriginalFilename
                request.addResource(
                    with: .photo,
                    fileURL: imported.photoURL,
                    options: photoOptions
                )

                let videoOptions = PHAssetResourceCreationOptions()
                videoOptions.shouldMoveFile = false
                videoOptions.originalFilename = imported.pairedVideoOriginalFilename
                request.addResource(
                    with: .pairedVideo,
                    fileURL: imported.pairedVideoURL,
                    options: videoOptions
                )
                createdLocalIdentifier = request.placeholderForCreatedAsset?.localIdentifier
            } completionHandler: { success, error in
                if success {
                    continuation.resume(returning: ())
                } else {
                    continuation.resume(
                        throwing: LivePhotoPipelineError.exportFailed(
                            error?.localizedDescription ?? "系统照片资料库拒绝了写入"
                        )
                    )
                }
            }
        }
        guard let createdLocalIdentifier else {
            throw LivePhotoPipelineError.roundTripVerificationFailed
        }
        let createdAssets = PHAsset.fetchAssets(
            withLocalIdentifiers: [createdLocalIdentifier],
            options: nil
        )
        guard let createdAsset = createdAssets.firstObject,
              createdAsset.mediaSubtypes.contains(.photoLive) else {
            throw LivePhotoPipelineError.roundTripVerificationFailed
        }
        _ = try LivePhotoResourceClassifier.classify(
            PHAssetResource.assetResources(for: createdAsset)
        )
        return createdLocalIdentifier
    }
}
