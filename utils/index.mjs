import execa from 'execa'
import createThemesJsonFile from './themes-json'
import { createNewThemesImgs, createMd } from './themes-extras'

const main = async() => {
    try {
        await createThemesJsonFile()
        let newThemes = await execa.stdout('git', [ '-C', '..', 'ls-files', '--others', '--exclude-standard'])
        await createNewThemesImgs(newThemes.split('\n'))
        await createMd()
    }catch(err) {
        console.log(err)
    }
} 

main()