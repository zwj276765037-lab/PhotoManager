import SwiftUI

struct ContentView: View {
    @StateObject private var model = LivePhotoViewModel()

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    header
                    preview
                    status
                    actions
                    milestone
                }
                .padding(20)
            }
            .background(Color(red: 0.045, green: 0.05, blue: 0.055))
            .foregroundStyle(Color(red: 0.95, green: 0.92, blue: 0.86))
            .toolbarColorScheme(.dark, for: .navigationBar)
            .sheet(isPresented: $model.isPickerPresented) {
                LivePhotoPicker { localIdentifier in
                    Task { @MainActor in
                        model.handlePickerSelection(localIdentifier)
                    }
                }
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("NATIVE LIVE PHOTO / P0")
                .font(.caption.weight(.bold))
                .tracking(2)
                .foregroundStyle(Color(red: 0.84, green: 1, blue: 0.25))
            Text("原生读取，\n原生写回。")
                .font(.system(size: 48, weight: .semibold, design: .serif))
                .minimumScaleFactor(0.8)
            Text("直接选择 iPhone Live Photo。App 自动读取静态原图与 pairedVideo，用户不再手动“存储为视频”。")
                .font(.body)
                .foregroundStyle(.secondary)
        }
    }

    @ViewBuilder
    private var preview: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 4)
                .fill(Color.black)
            if let livePhoto = model.preview {
                LivePhotoPlayerView(livePhoto: livePhoto)
            } else {
                VStack(spacing: 12) {
                    Image(systemName: "livephoto")
                        .font(.system(size: 44, weight: .light))
                    Text("选择后在这里原生播放")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .aspectRatio(4 / 5, contentMode: .fit)
        .clipShape(RoundedRectangle(cornerRadius: 4))
        .overlay(alignment: .bottomLeading) {
            Text(model.imported == nil ? "LIVE / WAITING" : "LIVE / PAIRED")
                .font(.caption2.weight(.bold))
                .tracking(1.5)
                .padding(14)
                .foregroundStyle(Color(red: 0.84, green: 1, blue: 0.25))
        }
    }

    private var status: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(model.statusTitle)
                    .font(.headline)
                Spacer()
                if model.isBusy {
                    ProgressView()
                        .tint(Color(red: 0.84, green: 1, blue: 0.25))
                }
            }
            Text(model.statusDetail)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            if model.isBusy {
                ProgressView(value: model.progress)
                    .tint(Color(red: 0.84, green: 1, blue: 0.25))
            }
            if let summary = model.importSummary {
                Text(summary)
                    .font(.caption.monospacedDigit())
                    .foregroundStyle(Color(red: 0.44, green: 0.66, blue: 1))
            }
        }
        .padding(16)
        .background(Color.white.opacity(0.055), in: RoundedRectangle(cornerRadius: 14))
    }

    private var actions: some View {
        VStack(spacing: 12) {
            Button(action: model.requestPicker) {
                Label("选择原生 Live Photo", systemImage: "photo.on.rectangle")
                    .frame(maxWidth: .infinity, minHeight: 54)
            }
            .buttonStyle(.borderedProminent)
            .tint(Color(red: 0.94, green: 0.32, blue: 0.21))
            .disabled(model.isBusy)

            Button(action: model.saveRoundTripCopy) {
                Label("验证原生 Live Photo 写回", systemImage: "livephoto.badge.arrow.down")
                    .frame(maxWidth: .infinity, minHeight: 54)
            }
            .buttonStyle(.bordered)
            .tint(Color(red: 0.84, green: 1, blue: 0.25))
            .disabled(model.imported == nil || model.isBusy)
        }
    }

    private var milestone: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("当前里程碑")
                .font(.caption.weight(.bold))
                .tracking(1.5)
            Text("先验证同一 PHAsset 的照片＋pairedVideo 能完整读取、预览并重新写回。此版本写回的是不修改画面的副本；通过真机验收后，再接入逐帧杂志合成与新的 Live Photo 元数据生成。")
                .font(.footnote)
                .foregroundStyle(.secondary)
        }
    }
}

