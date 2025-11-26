#include <iostream>
#include <string>
#include <fstream>
#include <filesystem>
#include <functional>
#include <vector>

namespace fs = std::filesystem;

// DDNet map format structures (based on DDNet source)
#pragma pack(1)
struct CMapItemVersion {
    int m_Version;
};

struct CMapItemInfo {
    int m_Version;
    int m_Author;
    int m_MapVersion;
    int m_Credits;
    int m_License;
};

struct CMapItemImage {
    int m_Version;
    int m_Width;
    int m_Height;
    int m_External;
    int m_ImageName;
    int m_ImageData;
};

struct CMapItemGroup {
    int m_Version;
    int m_OffsetX;
    int m_OffsetY;
    int m_ParallaxX;
    int m_ParallaxY;
    int m_StartLayer;
    int m_NumLayers;
    int m_UseClipping;
    int m_ClipX;
    int m_ClipY;
    int m_ClipW;
    int m_ClipH;
};

struct CMapItemLayer {
    int m_Version;
    int m_Type;
    int m_Flags;
};

// Layer types
enum {
    LAYERTYPE_INVALID = 0,
    LAYERTYPE_GAME,
    LAYERTYPE_TILES,
    LAYERTYPE_QUADS,
    LAYERTYPE_FRONT,
    LAYERTYPE_TELE,
    LAYERTYPE_SPEEDUP,
    LAYERTYPE_SWITCH,
    LAYERTYPE_TUNE,
    LAYERTYPE_SOUNDS_DEPRECATED, // deprecated! do not use this, this is just for compatibility reasons
    LAYERTYPE_SOUNDS,
};

struct CMapItemLayerTilemap {
    CMapItemLayer m_Layer;
    int m_Version;
    int m_Width;
    int m_Height;
    int m_Flags;
    int m_Color[4];
    int m_ColorEnv;
    int m_ColorEnvOffset;
    int m_Image;
    int m_Data;
    int m_tele;
    int m_speedup;
    int m_front;
    int m_switch;
    int m_tune;
};

// Game objects and items
enum {
    ITEM_NULL=0,
    ITEM_VERSION,
    ITEM_INFO,
    ITEM_IMAGE,
    ITEM_ENVELOPE,
    ITEM_GROUP,
    ITEM_LAYER,
    ITEM_ENVPOINTS,
    ITEM_SOUND,
    ITEM_AUTOMAPPER,
};

// Game layer tiles
enum {
    TILE_AIR=0,
    TILE_SOLID,
    TILE_DEATH,
    TILE_NOHOOK,
    TILE_NOLASER,
    TILE_THROUGH_CUT,
    TILE_THROUGH,
    TILE_JUMP,
    TILE_FREEZE = 9,
    TILE_TELEINEVIL = 10,
    TILE_UNFREEZE,
    TILE_DFREEZE,
    TILE_DUNFREEZE,
    TILE_TELEINWEAPON,
    TILE_TELEINHOOK,
    TILE_WALLJUMP = 16,
    TILE_EHOOK_START = 17,
    TILE_EHOOK_END,
    TILE_HIT_START = 19,
    TILE_HIT_END,
    TILE_SOLO_START,
    TILE_SOLO_END,
    TILE_SWITCHTIMEDOPEN = 22,
    TILE_SWITCHTIMEDCLOSE,
    TILE_SWITCHOPEN = 24,
    TILE_SWITCHCLOSE,
    TILE_TELEIN = 26,
    TILE_TELEOUT,
    TILE_BOOST,
    TILE_TELECHECK,
    TILE_TELECHECKOUT,
    TILE_TELECHECKIN,
    TILE_REFILL_JUMPS = 32,
    TILE_BEGIN,
    TILE_END,
    TILE_STOP = 60,
    TILE_STOPS,
    TILE_STOPA,
    TILE_TELECHECKINEVIL = 63,
    TILE_CP = 64,
    TILE_CP_F,
    TILE_THROUGH_ALL,
    TILE_THROUGH_DIR,
    TILE_TUNE1,
    TILE_OLDLASER = 71,
    TILE_NPC,
    TILE_EHOOK,
    TILE_NOHIT,
    TILE_NPH,
    TILE_UNLOCK_TEAM,
    TILE_PENALTY = 79,
    TILE_NPC_END = 88,
    TILE_SUPER_END,
    TILE_JETPACK_END,
    TILE_NPH_END,
    TILE_BONUS = 95,
};

struct CQuad {
    int m_aPoints[5*2];
    int m_aTexcoords[4*2];
    int m_aColors[4*4];
    int m_PosEnv;
    int m_PosEnvOffset;
    int m_ColorEnv;
    int m_ColorEnvOffset;
};

struct CTile {
    unsigned char m_Index;
    unsigned char m_Flags;
    unsigned char m_Skip;
    unsigned char m_Reserved;
};

struct CSpeedupTile {
    unsigned char m_Force;
    unsigned char m_MaxSpeed;
    unsigned char m_Type;
    unsigned char m_Angle;
    short m_MaxX;
    short m_MaxY;
};

struct CSwitchTile {
    unsigned char m_Number;
    unsigned char m_Type;
    unsigned char m_Flags;
    unsigned char m_Delay;
    unsigned char m_Reserved[2];
};

struct CTuneTile {
    unsigned char m_Number;
    unsigned char m_Type;
    int m_Value;
};

struct CEntity {
    int m_X;
    int m_Y;
    int m_Type;
    int m_Subtype;
};

// DDNet map file header
struct MapHeader {
    char magic[4];  // "DATA"
    int version;
    int size;
    int swaplen;
    int num_item_types;
    int num_items;
    int num_raw_data;
    int item_size;
    int data_size;
};

class MapInfo {
public:
    static bool read_map_header(const std::string& mapPath, MapHeader& header) {
        std::ifstream file(mapPath, std::ios::binary);
        if (!file.is_open()) {
            std::cout << "Cannot open map file for reading" << std::endl;
            return false;
        }

        // Read header
        file.read(reinterpret_cast<char*>(&header), sizeof(MapHeader));
        if (!file) {
            std::cout << "Failed to read map header" << std::endl;
            return false;
        }

        // Verify magic number
        if (strncmp(header.magic, "DATA", 4) != 0) {
            std::cout << "Invalid map format" << std::endl;
            return false;
        }

        return true;
    }

    static bool modify_map_data(const std::string& mapPath, const std::function<void(std::vector<char>&)>& modifier) {
        // First read the entire file
        std::ifstream inFile(mapPath, std::ios::binary | std::ios::ate);
        if (!inFile.is_open()) {
            std::cout << "Cannot open map file for reading" << std::endl;
            return false;
        }

        // Get file size and read the data
        std::streamsize size = inFile.tellg();
        inFile.seekg(0, std::ios::beg);
        
        std::vector<char> buffer(size);
        if (!inFile.read(buffer.data(), size)) {
            std::cout << "Failed to read map data" << std::endl;
            return false;
        }
        inFile.close();

        // Let the modifier function change the buffer
        modifier(buffer);

        // Write the modified data back
        std::ofstream outFile(mapPath, std::ios::binary);
        if (!outFile.is_open()) {
            std::cout << "Cannot open map file for writing" << std::endl;
            return false;
        }

        outFile.write(buffer.data(), buffer.size());
        if (!outFile) {
            std::cout << "Failed to write modified map data" << std::endl;
            return false;
        }

        return true;
    }

    static bool modify_map_info(const std::string& mapPath, const std::string& author, const std::string& mapVersion, const std::string& credits) {
        return modify_map_data(mapPath, [&](std::vector<char>& buffer) {
            // Find the info item in the map file
            const char* data = buffer.data();
            size_t size = buffer.size();
            
            // Skip header
            size_t pos = sizeof(MapHeader);
            
            while (pos < size) {
                // Look for Info item signature
                if (pos + sizeof(CMapItemInfo) <= size) {
                    CMapItemInfo* info = (CMapItemInfo*)(data + pos);
                    if (info->m_Version == 1) {  // Version 1 is standard for map info
                        // Found the info section, now we can modify it
                        // Note: String data is stored in the data section
                        info->m_Version = 1;  // Keep version
                        // Update other fields as needed
                        break;
                    }
                }
                pos += sizeof(CMapItemInfo);
            }
        });
    }

    static bool modify_map_layer(const std::string& mapPath, int layerIndex, const std::function<void(CMapItemLayer*)>& modifier) {
        return modify_map_data(mapPath, [&](std::vector<char>& buffer) {
            // Find the specified layer in the map file
            const char* data = buffer.data();
            size_t size = buffer.size();
            
            // Skip header
            size_t pos = sizeof(MapHeader);
            int currentLayer = 0;
            
            while (pos < size) {
                if (pos + sizeof(CMapItemLayer) <= size) {
                    CMapItemLayer* layer = (CMapItemLayer*)(data + pos);
                    if (currentLayer == layerIndex) {
                        // Found the target layer, modify it
                        modifier(layer);
                        break;
                    }
                    currentLayer++;
                }
                pos += sizeof(CMapItemLayer);
            }
        });
    }

    static bool modify_tilemap_layer(const std::string& mapPath, int layerIndex, const std::function<void(CMapItemLayerTilemap*)>& modifier) {
        return modify_map_data(mapPath, [&](std::vector<char>& buffer) {
            // Find the specified tilemap layer in the map file
            const char* data = buffer.data();
            size_t size = buffer.size();
            
            // Skip header
            size_t pos = sizeof(MapHeader);
            int currentLayer = 0;
            
            while (pos < size) {
                if (pos + sizeof(CMapItemLayerTilemap) <= size) {
                    CMapItemLayerTilemap* layer = (CMapItemLayerTilemap*)(data + pos);
                    if (currentLayer == layerIndex && layer->m_Layer.m_Type == LAYERTYPE_TILES) {
                        // Found the target tilemap layer, modify it
                        modifier(layer);
                        break;
                    }
                    currentLayer++;
                }
                pos += sizeof(CMapItemLayerTilemap);
            }
        });
    }

    static bool modify_entity(const std::string& mapPath, int entityIndex, const std::function<void(CEntity*)>& modifier) {
        return modify_map_data(mapPath, [&](std::vector<char>& buffer) {
            const char* data = buffer.data();
            size_t size = buffer.size();
            size_t pos = sizeof(MapHeader);
            int currentEntity = 0;
            
            while (pos < size) {
                if (pos + sizeof(CEntity) <= size) {
                    CEntity* entity = (CEntity*)(data + pos);
                    if (currentEntity == entityIndex) {
                        modifier(entity);
                        break;
                    }
                    currentEntity++;
                }
                pos += sizeof(CEntity);
            }
        });
    }

    static bool modify_tiles(const std::string& mapPath, int layerIndex, const std::function<void(CTile*, int width, int height)>& modifier) {
        return modify_map_data(mapPath, [&](std::vector<char>& buffer) {
            const char* data = buffer.data();
            size_t size = buffer.size();
            size_t pos = sizeof(MapHeader);
            int currentLayer = 0;
            
            while (pos < size) {
                if (pos + sizeof(CMapItemLayerTilemap) <= size) {
                    CMapItemLayerTilemap* layer = (CMapItemLayerTilemap*)(data + pos);
                    if (currentLayer == layerIndex && layer->m_Layer.m_Type == LAYERTYPE_TILES) {
                        // Found the tilemap layer, now find the tile data
                        size_t tileDataPos = layer->m_Data;
                        if (tileDataPos + (layer->m_Width * layer->m_Height * sizeof(CTile)) <= size) {
                            CTile* tiles = (CTile*)(data + tileDataPos);
                            modifier(tiles, layer->m_Width, layer->m_Height);
                        }
                        break;
                    }
                    currentLayer++;
                }
                pos += sizeof(CMapItemLayerTilemap);
            }
        });
    }

    static bool add_entity(const std::string& mapPath, const CEntity& entity) {
        return modify_map_data(mapPath, [&](std::vector<char>& buffer) {
            // This is a simplified version - in reality, you need to:
            // 1. Find the game layer
            // 2. Ensure there's space in the data section
            // 3. Add the entity to the correct position
            // 4. Update all necessary offsets and counts
            
            // This is just a placeholder showing the concept
            buffer.insert(buffer.end(), 
                        reinterpret_cast<const char*>(&entity),
                        reinterpret_cast<const char*>(&entity) + sizeof(CEntity));
        });
    }

    static bool set_tile(const std::string& mapPath, int layerIndex, int x, int y, unsigned char tileIndex, unsigned char flags = 0) {
        return modify_tiles(mapPath, layerIndex, [x, y, tileIndex, flags](CTile* tiles, int width, int height) {
            if (x >= 0 && x < width && y >= 0 && y < height) {
                int index = y * width + x;
                tiles[index].m_Index = tileIndex;
                tiles[index].m_Flags = flags;
            }
        });
    }

    static std::vector<std::pair<int, int>> find_tiles(const std::string& mapPath, int layerIndex, unsigned char tileType) {
        std::vector<std::pair<int, int>> positions;
        
        modify_tiles(mapPath, layerIndex, [tileType, &positions](CTile* tiles, int width, int height) {
            for (int y = 0; y < height; y++) {
                for (int x = 0; x < width; x++) {
                    int index = y * width + x;
                    if (tiles[index].m_Index == tileType) {
                        positions.push_back({x, y});
                    }
                }
            }
        });
        
        return positions;
    }

    static void print_freeze_tiles(const std::string& mapPath) {
        std::cout << "Scanning for freeze tiles..." << std::endl;
        
        // Look in all layers
        int currentLayer = 0;
        bool foundAny = false;
        
        while (true) {
            auto freezePositions = find_tiles(mapPath, currentLayer, TILE_FREEZE);
            auto dfreezePositions = find_tiles(mapPath, currentLayer, TILE_DFREEZE);
            
            if (!freezePositions.empty()) {
                std::cout << "\nLayer " << currentLayer << " Freeze tiles:" << std::endl;
                for (const auto& pos : freezePositions) {
                    std::cout << "  Position: x=" << pos.first << ", y=" << pos.second << std::endl;
                }
                foundAny = true;
            }
            
            if (!dfreezePositions.empty()) {
                std::cout << "\nLayer " << currentLayer << " Deep Freeze tiles:" << std::endl;
                for (const auto& pos : dfreezePositions) {
                    std::cout << "  Position: x=" << pos.first << ", y=" << pos.second << std::endl;
                }
                foundAny = true;
            }
            
            if (freezePositions.empty() && dfreezePositions.empty()) {
                // If we've gone through several empty layers, assume we're done
                if (currentLayer > 5) break;
            }
            
            currentLayer++;
        }
        
        if (!foundAny) {
            std::cout << "No freeze tiles found in the map." << std::endl;
        }
    }

    // Print map information
    static void print_map_info(const std::string& mapPath) {
        MapHeader header;
        if (!read_map_header(mapPath, header)) {
            return;
        }

        std::cout << "Map Information:" << std::endl;
        std::cout << "Version: " << header.version << std::endl;
        std::cout << "Size: " << header.size << " bytes" << std::endl;
        std::cout << "Number of item types: " << header.num_item_types << std::endl;
        std::cout << "Number of items: " << header.num_items << std::endl;
        std::cout << "Number of raw data: " << header.num_raw_data << std::endl;
    }
};
