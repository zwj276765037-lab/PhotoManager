import Foundation
import Photos

final class LivePhotoImportService {
    func importLivePhoto(
        localIdentifier: String,
        progress: @escaping (Double) -> Void
    ) async throws -> ImportedLivePhoto {
        let fetchResult = PHAsset.fetchAssets(
            withLocalIdentifiers: [localIdentifier],
            options: nil
        )
        guard let asset = fetchResult.firstObject else {
            throw LivePhotoPipelineError.assetNotFound
        }
        guard asset.mediaType == .image, asset.mediaSubtypes.contains(.photoLive) else {
            throw LivePhotoPipelineError.notLivePhoto
        }

        let resources = try LivePhotoResourceClassifier.classify(
            PHAssetResource.assetResources(for: asset)
        )
        let directory = try makeWorkingDirectory()
        let photoURL = outputURL(
            in: directory,
            stem: "source-photo",
            resource: resources.photo,
            fallbackExtension: "heic"
        )
        let pairedVideoURL = outputURL(
            in: directory,
            stem: "source-paired-video",
            resource: resources.pairedVideo,
            fallbackExtension: "mov"
        )

        try await writeResource(resources.photo, to: photoURL) { value in
            progress(value * 0.45)
        }
        try await writeResource(resources.pairedVideo, to: pairedVideoURL) { value in
            progress(0.45 + value * 0.55)
        }
        progress(1)

        return ImportedLivePhoto(
            assetLocalIdentifier: localIdentifier,
            photoURL: photoURL,
            pairedVideoURL: pairedVideoURL,
            photoOriginalFilename: resources.photo.originalFilename,
            pairedVideoOriginalFilename: resources.pairedVideo.originalFilename,
            photoUniformTypeIdentifier: resources.photo.uniformTypeIdentifier,
            pairedVideoUniformTypeIdentifier: resources.pairedVideo.uniformTypeIdentifier
        )
    }

    private func makeWorkingDirectory() throws -> URL {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("PhotoManager", isDirectory: true)
        let directory = root.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(
            at: directory,
            withIntermediateDirectories: true
        )
        return directory
    }

    private func outputURL(
        in directory: URL,
        stem: String,
        resource: PHAssetResource,
        fallbackExtension: String
    ) -> URL {
        let originalExtension = URL(fileURLWithPath: resource.originalFilename).pathExtension
        let pathExtension = originalExtension.isEmpty ? fallbackExtension : originalExtension
        return directory.appendingPathComponent(stem).appendingPathExtension(pathExtension)
    }

    private func writeResource(
        _ resource: PHAssetResource,
        to destination: URL,
        progress: @escaping (Double) -> Void
    ) async throws {
        let _: Void = try await withCheckedThrowingContinuation { continuation in
            let options = PHAssetResourceRequestOptions()
            options.isNetworkAccessAllowed = true
            options.progressHandler = { value in
                progress(value)
            }
            PHAssetResourceManager.default().writeData(
                for: resource,
                toFile: destination,
                options: options
            ) { error in
                if let error {
                    continuation.resume(throwing: error)
                } else {
                    continuation.resume(returning: ())
                }
            }
        }
    }
}
