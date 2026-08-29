import Photos
import SwiftUI

@MainActor
final class LivePhotoViewModel: ObservableObject {
    @Published var isPickerPresented = false
    @Published var isBusy = false
    @Published var progress = 0.0
    @Published var statusTitle = "等待选择原生 Live Photo"
    @Published var statusDetail = "不需要先存储为视频"
    @Published var imported: ImportedLivePhoto?
    @Published var preview: PHLivePhoto?

    private let importer = LivePhotoImportService()
    private let exporter = LivePhotoExportService()
    private let imageManager = PHImageManager.default()
    private var previewRequestID: PHImageRequestID?

    func requestPicker() {
        guard !isBusy else { return }
        Task {
            statusTitle = "正在请求照片权限"
            statusDetail = "只读取你主动选择的 Live Photo"
            let authorization = await PHPhotoLibrary.requestAuthorization(for: .readWrite)
            guard authorization == .authorized || authorization == .limited else {
                showError(LivePhotoPipelineError.readPermissionDenied)
                return
            }
            statusTitle = "请选择一张 Live Photo"
            statusDetail = "系统选择器只显示原生 Live Photo"
            isPickerPresented = true
        }
    }

    func handlePickerSelection(_ localIdentifier: String?) {
        isPickerPresented = false
        guard let localIdentifier else {
            statusTitle = "没有选择照片"
            statusDetail = "可以重新打开系统选择器"
            return
        }

        isBusy = true
        progress = 0
        imported = nil
        preview = nil
        statusTitle = "正在读取原生资源"
        statusDetail = "自动取得照片与配对视频，不需要手动转换"

        Task {
            do {
                let result = try await importer.importLivePhoto(
                    localIdentifier: localIdentifier
                ) { [weak self] value in
                    Task { @MainActor in
                        self?.progress = value
                    }
                }
                imported = result
                isBusy = false
                progress = 1
                statusTitle = "原生 Live Photo 已就绪"
                statusDetail = "照片与 pairedVideo 已绑定到同一个本地任务"
                requestPreview(localIdentifier: localIdentifier)
            } catch {
                showError(error)
            }
        }
    }

    func saveRoundTripCopy() {
        guard let imported, !isBusy else { return }
        isBusy = true
        statusTitle = "正在写回 Live Photo"
        statusDetail = "系统将创建一张新的原生 Live Photo，不修改原件"

        Task {
            do {
                let createdIdentifier = try await exporter.saveAsNewLivePhoto(imported)
                isBusy = false
                statusTitle = "原生写回成功"
                statusDetail = "已重新读取照片与 pairedVideo；请到“照片”中按住新作品验证动作"
                requestPreview(localIdentifier: createdIdentifier)
            } catch {
                showError(error)
            }
        }
    }

    var importSummary: String? {
        guard let imported else { return nil }
        return "照片：\(imported.photoOriginalFilename) · \(imported.photoUniformTypeIdentifier) · \(formatBytes(imported.photoByteCount))\n配对视频：\(imported.pairedVideoOriginalFilename) · \(imported.pairedVideoUniformTypeIdentifier) · \(formatBytes(imported.pairedVideoByteCount))"
    }

    private func requestPreview(localIdentifier: String) {
        if let previewRequestID {
            imageManager.cancelImageRequest(previewRequestID)
        }
        let result = PHAsset.fetchAssets(
            withLocalIdentifiers: [localIdentifier],
            options: nil
        )
        guard let asset = result.firstObject else { return }

        let options = PHLivePhotoRequestOptions()
        options.deliveryMode = .highQualityFormat
        options.isNetworkAccessAllowed = true
        previewRequestID = imageManager.requestLivePhoto(
            for: asset,
            targetSize: CGSize(width: 1200, height: 1500),
            contentMode: .aspectFit,
            options: options
        ) { [weak self] livePhoto, _ in
            guard let livePhoto else { return }
            Task { @MainActor in
                self?.preview = livePhoto
            }
        }
    }

    private func showError(_ error: Error) {
        isBusy = false
        statusTitle = "没有完成"
        statusDetail = error.localizedDescription
    }

    private func formatBytes(_ bytes: Int64) -> String {
        ByteCountFormatter.string(fromByteCount: bytes, countStyle: .file)
    }
}
