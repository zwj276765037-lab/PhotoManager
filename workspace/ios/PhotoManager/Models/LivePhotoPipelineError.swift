import Foundation

enum LivePhotoPipelineError: LocalizedError {
    case readPermissionDenied
    case addPermissionDenied
    case missingAssetIdentifier
    case assetNotFound
    case notLivePhoto
    case missingPhotoResource
    case missingPairedVideoResource
    case roundTripVerificationFailed
    case exportFailed(String)

    var errorDescription: String? {
        switch self {
        case .readPermissionDenied:
            return "没有获得读取照片资料库的权限"
        case .addPermissionDenied:
            return "没有获得把 Live Photo 写回照片资料库的权限"
        case .missingAssetIdentifier:
            return "系统选择器没有返回原生照片资产标识"
        case .assetNotFound:
            return "找不到刚才选择的照片资产"
        case .notLivePhoto:
            return "选择的资产不是原生 Live Photo"
        case .missingPhotoResource:
            return "Live Photo 缺少静态照片资源"
        case .missingPairedVideoResource:
            return "Live Photo 缺少配对视频资源"
        case .roundTripVerificationFailed:
            return "系统已返回保存结果，但重新读取时没有找到完整的 Live Photo 资源对"
        case .exportFailed(let message):
            return "Live Photo 写回失败：\(message)"
        }
    }
}
