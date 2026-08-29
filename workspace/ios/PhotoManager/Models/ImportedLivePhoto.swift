import Foundation

struct ImportedLivePhoto: Identifiable {
    let id = UUID()
    let assetLocalIdentifier: String
    let photoURL: URL
    let pairedVideoURL: URL
    let photoOriginalFilename: String
    let pairedVideoOriginalFilename: String
    let photoUniformTypeIdentifier: String
    let pairedVideoUniformTypeIdentifier: String

    var photoByteCount: Int64 {
        fileSize(at: photoURL)
    }

    var pairedVideoByteCount: Int64 {
        fileSize(at: pairedVideoURL)
    }

    private func fileSize(at url: URL) -> Int64 {
        let values = try? url.resourceValues(forKeys: [.fileSizeKey])
        return Int64(values?.fileSize ?? 0)
    }
}
