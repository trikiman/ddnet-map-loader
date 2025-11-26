# Current Tasks - General Channel Implementation

## Features to Implement

### 1. Map Upload Handler
- [ ] Add message handler for file attachments
- [ ] Check if attachment is a .map file
- [ ] Download map file to appropriate directory
- [ ] Validate map file structure
- [ ] Simulate double click to load map

### 2. Reaction System
- [ ] Add confirmation emoji when map processing starts
- [ ] Update emoji when processing completes
- [ ] Add error emoji if processing fails
- [ ] Add status message with processing details

### 3. Interactive Reactions
- [ ] Add reaction click handler
- [ ] Verify if clicked emoji is on a map message
- [ ] Re-process map when emoji is clicked
- [ ] Update emoji status based on reprocessing result

### 4. Map List Command (✅ Done)
- [x] Show last 20 maps in folder
- [x] Format with proper spacing
- [x] Include timestamps
- [x] Sort by most recent

### 5. Hot Reload Command (✅ Done)
- [x] Get current map name
- [x] Validate map exists
- [x] Perform hot reload
- [x] Show success/failure message

## Implementation Order
1. Map Upload Handler - Most critical for basic functionality
2. Reaction System - Provides user feedback
3. Interactive Reactions - Enhances user experience

## Notes
- All features should handle errors gracefully
- Provide clear feedback to users
- Maintain consistent formatting
- Follow existing code style