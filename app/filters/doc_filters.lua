-- text_color_and_align.lua

-- ==========================================
-- 1. SPAN PROCESSOR (For Text & Background Colors)
-- ==========================================
function Span(el)
  local style = el.attributes['style']
  if not style then return nil end

  local color_val = nil
  local bg_val = nil

  -- Loop through all CSS properties to prevent 'background-color' from matching 'color'
  for prop, hex in style:gmatch('([%a%-]+):%s*(#[%da-fA-F]+)') do
    if prop == 'color' then
      color_val = hex:sub(2):upper()
    elseif prop == 'background-color' then
      bg_val = hex:sub(2):upper()
    end
  end
  
  if not color_val and not bg_val then return nil end

  -- For Raw LaTeX
  if FORMAT:match 'latex' or FORMAT:match 'beamer' then
    if bg_val then
      table.insert(el.content, 1, pandoc.RawInline('latex', '\\colorbox[HTML]{' .. bg_val .. '}{'))
      table.insert(el.content, pandoc.RawInline('latex', '}'))
    end
    if color_val then
      table.insert(el.content, 1, pandoc.RawInline('latex', '\\textcolor[HTML]{' .. color_val .. '}{'))
      table.insert(el.content, pandoc.RawInline('latex', '}'))
    end
    return el

  elseif FORMAT:match 'typst' or FORMAT:match 'pdf' then
    if color_val then
      table.insert(el.content, 1, pandoc.RawInline('typst', '#text(fill: rgb("#' .. color_val .. '"))['))
      table.insert(el.content, pandoc.RawInline('typst', ']'))
    end
    if bg_val then
      table.insert(el.content, 1, pandoc.RawInline('typst', '#highlight(fill: rgb("#' .. bg_val .. '"))['))
      table.insert(el.content, pandoc.RawInline('typst', ']'))
    end
    return el

  -- For Word (DOCX)
  elseif FORMAT:match 'docx' then
    local styleName = ""
    
    if color_val then styleName = styleName .. "Color" .. color_val end
    if bg_val then styleName = styleName .. "Bg" .. bg_val end
    
    el.attributes['custom-style'] = styleName
    el.attributes['style'] = nil 
    return el
  end
end

-- ==========================================
-- 2. DIV PROCESSOR (For Block Alignment)
-- ==========================================
function Div(el)
  local c_style = el.attributes['custom-style']
  if not c_style then return nil end

  local align = c_style:match('^align%-(.+)$')
  if not align then return nil end

  -- For Raw LaTeX
  if FORMAT:match 'latex' or FORMAT:match 'beamer' then
    local env = nil
    if align == 'center' then 
      env = 'center'
    elseif align == 'right' then 
      env = 'flushright'
    end
    
    if env then
      local blocks = { pandoc.RawBlock('latex', '\\begin{' .. env .. '}') }
      for _, b in ipairs(el.content) do
        table.insert(blocks, b)
      end
      table.insert(blocks, pandoc.RawBlock('latex', '\\end{' .. env .. '}'))
      return blocks
    end
    return el

  elseif FORMAT:match 'typst' or FORMAT:match 'pdf' then
    local blocks = {}
    
    if align == 'center' or align == 'right' then
      table.insert(blocks, pandoc.RawBlock('typst', '#align(' .. align .. ')['))
    elseif align == 'justify' then
      table.insert(blocks, pandoc.RawBlock('typst', '#par(justify: true)['))
    end
    
    -- If we have an alignment block, insert the original contents and close it
    if #blocks > 0 then
      for _, b in ipairs(el.content) do
        table.insert(blocks, b)
      end
      table.insert(blocks, pandoc.RawBlock('typst', ']'))
      return blocks
    end
    
    return el

  -- For Word (DOCX)
  elseif FORMAT:match 'docx' then
    return el
  end
end