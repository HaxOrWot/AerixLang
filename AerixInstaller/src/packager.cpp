// packager.cpp — Packs a staged directory tree into a zlib-compressed ARXP archive.
// Usage: packager.exe <staging_dir> <output_payload.bin>

#include <zlib.h>
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace fs = std::filesystem;

namespace {

void append_u32(std::vector<uint8_t>& out, uint32_t v) {
    uint8_t b[4];
    std::memcpy(b, &v, 4);
    out.insert(out.end(), b, b + 4);
}

void append_u64(std::vector<uint8_t>& out, uint64_t v) {
    uint8_t b[8];
    std::memcpy(b, &v, 8);
    out.insert(out.end(), b, b + 8);
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: packager <staging_dir> <output_payload.bin>\n";
        return 1;
    }

    fs::path root(argv[1]);
    fs::path out_file(argv[2]);
    if (!fs::exists(root) || !fs::is_directory(root)) {
        std::cerr << "[ERROR] Staging directory not found: " << root.string() << "\n";
        return 1;
    }

    std::vector<fs::path> rel_files;
    for (const auto& entry : fs::recursive_directory_iterator(root)) {
        if (entry.is_regular_file()) {
            rel_files.push_back(fs::relative(entry.path(), root));
        }
    }
    std::sort(rel_files.begin(), rel_files.end(), [](const fs::path& a, const fs::path& b) {
        return a.generic_string() < b.generic_string();
    });

    std::vector<uint8_t> raw;
    for (const auto& rel : rel_files) {
        fs::path full = root / rel;
        std::ifstream in(full, std::ios::binary | std::ios::ate);
        if (!in) {
            std::cerr << "[ERROR] Failed to open file: " << full.string() << "\n";
            return 1;
        }
        std::streamsize sz = in.tellg();
        in.seekg(0, std::ios::beg);
        std::vector<uint8_t> data(static_cast<size_t>(sz));
        if (sz > 0 && !in.read(reinterpret_cast<char*>(data.data()), sz)) {
            std::cerr << "[ERROR] Failed to read file: " << full.string() << "\n";
            return 1;
        }

        std::string rel_utf8 = rel.generic_u8string();
        append_u32(raw, static_cast<uint32_t>(rel_utf8.size()));
        raw.insert(raw.end(), rel_utf8.begin(), rel_utf8.end());
        append_u64(raw, static_cast<uint64_t>(data.size()));
        raw.insert(raw.end(), data.begin(), data.end());
    }

    uLongf comp_bound = compressBound(static_cast<uLong>(raw.size()));
    std::vector<uint8_t> comp(comp_bound);
    int zrc = compress2(comp.data(), &comp_bound, raw.data(), static_cast<uLong>(raw.size()), Z_BEST_COMPRESSION);
    if (zrc != Z_OK) {
        std::cerr << "[ERROR] zlib compress2 failed with code " << zrc << "\n";
        return 1;
    }
    comp.resize(comp_bound);

    fs::create_directories(out_file.parent_path());
    std::ofstream out(out_file, std::ios::binary);
    if (!out) {
        std::cerr << "[ERROR] Failed to open output: " << out_file.string() << "\n";
        return 1;
    }

    const char magic[4] = {'A', 'R', 'X', 'P'};
    uint32_t format_ver = 1;
    uint32_t file_count = static_cast<uint32_t>(rel_files.size());
    uint64_t raw_size = static_cast<uint64_t>(raw.size());

    out.write(magic, 4);
    out.write(reinterpret_cast<const char*>(&format_ver), sizeof(format_ver));
    out.write(reinterpret_cast<const char*>(&file_count), sizeof(file_count));
    out.write(reinterpret_cast<const char*>(&raw_size), sizeof(raw_size));
    out.write(reinterpret_cast<const char*>(comp.data()), static_cast<std::streamsize>(comp.size()));
    out.close();

    std::cout << "[OK] Packed " << file_count << " files ("
              << raw_size << " bytes raw -> " << comp.size() << " bytes compressed)\n";
    return 0;
}
